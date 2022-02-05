import contextlib
from pathlib import Path, PurePath
from types import TracebackType
from typing import Dict, Iterator, Optional, Sequence, Type

from .logger import log
from .options import BuildOptions
from .platform_backend import PlatformBackend
from .typing import PathOrStr, assert_never
from .util import (
    NonPlatformWheelError,
    get_build_verbosity_extra_flags,
    prepare_command,
)
from .virtualenv import VirtualEnv, VirtualEnvBase


class BuilderBackend:
    def __init__(
        self,
        platform: PlatformBackend,
        identifier: str,
        base_python: PurePath,
        build_options: BuildOptions,
    ):
        self._platform = platform
        self._base_python = base_python
        self._build_options = build_options
        self._identifier = identifier
        self._venv: Optional[VirtualEnvBase] = None
        self._constraints_dict: Optional[Dict[str, str]] = None
        self._can_run = False
        self._closed = False
        self._running = False

    def __enter__(self) -> "BuilderBackend":
        assert not self._can_run
        assert not self._closed
        self._can_run = True
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._closed = True
        self._can_run = False

    @property
    def venv(self) -> VirtualEnvBase:
        assert self._venv is not None
        return self._venv

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def build_options(self) -> BuildOptions:
        return self._build_options

    @property
    def base_python(self) -> PurePath:
        return self._base_python

    @property
    def platform(self) -> PlatformBackend:
        return self._platform

    def call(self, *args: PathOrStr, env: Optional[Dict[str, str]] = None) -> None:
        self.venv.call(*args, env=env)

    def shell(self, command: str) -> None:
        self.venv.shell(command)

    def virtualenv(self, constraints: Optional[Path] = None) -> VirtualEnvBase:
        return VirtualEnv(self._platform, self._base_python, constraints)

    def venv_post_creation_patch(self) -> None:
        pass

    def update_build_env(self, env: Dict[str, str]) -> None:
        pass

    def get_extra_build_tools(self) -> Sequence[str]:
        return []

    def update_repair_kwargs(self, repair_kwargs: Dict[str, PathOrStr]) -> None:
        pass

    @property
    def skip_upgrade_pip(self) -> bool:
        return False

    @property
    def skip_install_build_tools(self) -> bool:
        return False

    @property
    def constraints_dict(self) -> Dict[str, str]:
        assert self._constraints_dict is not None
        return self._constraints_dict

    @contextlib.contextmanager
    def _setup_build_env(self) -> Iterator[None]:
        log.step("Setting up build environment...")
        # 1/ create the venv
        dependency_constraints = self.build_options.dependency_constraints
        constraints_path: Optional[Path] = None
        if dependency_constraints:
            constraints_path = dependency_constraints.get_for_identifier(self.identifier)
        with self.virtualenv(constraints_path) as venv:
            self._venv = venv
            # 2/ patch the venv, post-creation
            self.venv_post_creation_patch()
            # 3/ update pip (if constraint not handled in creation)
            if not self.skip_upgrade_pip:
                # upgrade pip to the version matching our constraints
                # if necessary, reinstall it to ensure that it's available on PATH as 'pip.exe'
                venv.install("--upgrade", "pip", use_constraints=True)

            # 4/ update env with results from CIBW_ENVIRONMENT
            venv.env = self.build_options.environment.as_dictionary(
                venv.env, self.platform.environment_executor
            )

            # 6/ checks
            venv.sanity_check()

            # 7/ update_build_environment
            self.update_build_env(venv.env)

            # 8/ yield valid venv
            yield

            # 9/ invalidate venv
            self._venv = None

    def _install_build_tools(self) -> None:
        if not self.skip_install_build_tools:
            log.step("Installing build tools...")
            build_tools = {
                "pip": ["setuptools", "wheel"],
                "build": ["build[virtualenv]"],
            }
            tools = build_tools[self.build_options.build_frontend]
            extras = self.get_extra_build_tools()
            self.venv.install("--upgrade", *tools, *extras, use_constraints=True)

    def _before_build(self) -> None:
        build_options = self.build_options
        # run the before_build command
        if build_options.before_build:
            log.step("Running before_build...")
            project_dir = self.platform.get_remote_path(Path("."))
            package_dir = self.platform.get_remote_path(build_options.package_dir.resolve())
            before_build_prepared = prepare_command(
                build_options.before_build, project=project_dir, package=package_dir
            )
            self.shell(before_build_prepared)

    def _build_wheel(self, built_wheel_dir: PurePath) -> PurePath:
        log.step("Building wheel...")
        build_options = self.build_options
        verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
        # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
        # see https://github.com/pypa/cibuildwheel/pull/369
        package_dir = self.platform.get_remote_path(build_options.package_dir.resolve())
        if build_options.build_frontend == "pip":
            self.call(
                "python",
                "-m",
                "pip",
                "wheel",
                package_dir,
                f"--wheel-dir={built_wheel_dir}",
                "--no-deps",
                *verbosity_flags,
            )
        elif build_options.build_frontend == "build":
            config_setting = " ".join(verbosity_flags)
            build_env = self.venv.env.copy()
            if self.venv.constraints_path:
                # Bug in pip <= 21.1.3 - we can't have a space in the
                # constraints file, and pip doesn't support drive letters
                # in uhi. After probably pip 21.2, we can use uri.
                assert " " not in str(self.venv.constraints_path)
                build_env["PIP_CONSTRAINT"] = str(self.venv.constraints_path)
                build_env["VIRTUALENV_PIP"] = str(self.venv.pip_version)
            self.call(
                "python",
                "-m",
                "build",
                package_dir,
                "--wheel",
                f"--outdir={built_wheel_dir}",
                f"--config-setting={config_setting}",
                env=build_env,
            )
        else:
            assert_never(build_options.build_frontend)

        built_wheel = next(self.platform.glob(built_wheel_dir, "*.whl"))
        if built_wheel.name.endswith("none-any.whl"):
            raise NonPlatformWheelError()
        return built_wheel

    def _repair_wheel(
        self, built_wheel: PurePath, repaired_wheel_dir: PurePath
    ) -> Sequence[PurePath]:
        build_options = self.build_options
        # repair the wheel
        if build_options.repair_command:
            log.step("Repairing wheel...")
            repair_kwargs: Dict[str, PathOrStr] = {
                "wheel": built_wheel,
                "dest_dir": repaired_wheel_dir,
            }
            self.update_repair_kwargs(repair_kwargs)
            repair_command_prepared = prepare_command(build_options.repair_command, **repair_kwargs)
            self.shell(repair_command_prepared)
        else:
            self.platform.move_files(built_wheel, dest=repaired_wheel_dir)

        return tuple(self.platform.glob(repaired_wheel_dir, "*.whl"))

    def run(self, repaired_wheel_dir: PurePath) -> Sequence[PurePath]:
        assert self._can_run
        assert not self._running
        self._running = True
        with self._setup_build_env():
            self._install_build_tools()
            self._before_build()
            with self.platform.tmp_dir(self.identifier + "-built-wheel") as built_wheel_dir:
                built_wheel = self._build_wheel(built_wheel_dir)
                wheels = self._repair_wheel(built_wheel, repaired_wheel_dir)
            # save build environment
            self._constraints_dict = self.venv.constraints_dict
        return wheels


def do_test_wheel(
    platform_backend: PlatformBackend,
    base_python: PurePath,
    constraints_dict: Dict[str, str],
    build_options: BuildOptions,
    repaired_wheel: PurePath,
    arch: Optional[str] = None,
) -> None:
    log.step("Testing wheel..." if arch is None else f"Testing wheel on {arch}...")
    with VirtualEnv(
        platform_backend, base_python, constraints_dict=constraints_dict, arch=arch
    ) as venv:
        # update env with results from CIBW_ENVIRONMENT
        venv.env = build_options.environment.as_dictionary(
            prev_environment=venv.env, executor=platform_backend.environment_executor
        )
        # check that we are using the Python from the virtual environment
        venv.which("python")

        prepare_kwargs = {
            "project": platform_backend.get_remote_path(Path(".").resolve()),
            "package": platform_backend.get_remote_path(build_options.package_dir.resolve()),
        }

        if build_options.before_test:
            before_test_prepared = prepare_command(build_options.before_test, **prepare_kwargs)
            venv.shell(before_test_prepared)

        # install the wheel
        venv.install(f"{repaired_wheel}{build_options.test_extras}")

        # test the wheel
        if build_options.test_requires:
            venv.install(*build_options.test_requires)

        # run the tests from $HOME, with an absolute path in the command
        # (this ensures that Python runs the tests against the installed wheel
        # and not the repo code)
        assert build_options.test_command is not None
        test_command_prepared = prepare_command(build_options.test_command, **prepare_kwargs)
        venv.shell(test_command_prepared, cwd=platform_backend.home)


def run_before_all(platform: PlatformBackend, options: BuildOptions, env: Dict[str, str]) -> None:
    if options.before_all:
        log.step("Running before_all...")
        prepare_kwargs = {
            "project": platform.get_remote_path(Path(".").resolve()),
            "package": platform.get_remote_path(options.package_dir.resolve()),
        }
        before_all_prepared = prepare_command(options.before_all, **prepare_kwargs)
        env = options.environment.as_dictionary(env, platform.environment_executor)
        platform.shell(before_all_prepared, env=env)
