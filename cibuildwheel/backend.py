import shutil
from pathlib import Path, PurePath
from typing import Dict, Iterable, Optional, Sequence

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
    BUILD_TOOLS = {
        "pip": ["setuptools", "wheel"],
        "build": ["build[virtualenv]"],
    }

    def __init__(self, build_options: BuildOptions, venv: VirtualEnvBase, identifier: str):
        self.build_options = build_options
        self.venv = venv
        self.identifier = identifier

    def call(self, *args: PathOrStr, env: Optional[Dict[str, str]] = None) -> None:
        self.venv.call(*args, env=env)

    def shell(self, command: str) -> None:
        self.venv.shell(command)

    def install_build_tools(self, extras: Iterable[str]) -> None:
        log.step("Installing build tools...")
        tools = BuilderBackend.BUILD_TOOLS[self.build_options.build_frontend]
        dependency_constraints_flags: Sequence[PathOrStr] = []
        dependency_constraints = self.build_options.dependency_constraints
        if dependency_constraints:
            # TODO generic (not used by linux for now)
            constraints_path = dependency_constraints.get_for_identifier(self.identifier)
            dependency_constraints_flags = ["-c", constraints_path]
        self.venv.install("--upgrade", *tools, *extras, *dependency_constraints_flags)

    def build(self, repaired_wheel_dir: PurePath) -> Sequence[PurePath]:
        build_options = self.build_options
        project_dir = self.venv.base.get_remote_path(Path("."))
        package_dir = self.venv.base.get_remote_path(build_options.package_dir.resolve())

        # run the before_build command
        if build_options.before_build:
            log.step("Running before_build...")
            before_build_prepared = prepare_command(
                build_options.before_build, project=project_dir, package=package_dir
            )
            self.shell(before_build_prepared)

        log.step("Building wheel...")
        verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
        with self.venv.base.tmp_dir("built_wheel") as built_wheel_dir:
            if build_options.build_frontend == "pip":
                # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                # see https://github.com/pypa/cibuildwheel/pull/369
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
                    # in uhi.  After probably pip 21.2, we can use uri.
                    if " " in str(self.venv.constraints_path):
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

            built_wheel = next(self.venv.base.glob(built_wheel_dir, "*.whl"))
            if built_wheel.name.endswith("none-any.whl"):
                raise NonPlatformWheelError()

            # repair the wheel
            if build_options.repair_command:
                log.step("Repairing wheel...")
                repair_kwargs: Dict[str, PathOrStr] = {
                    "wheel": built_wheel,
                    "dest_dir": repaired_wheel_dir,
                }
                self.update_repair_kwargs(repair_kwargs)
                repair_command_prepared = prepare_command(
                    build_options.repair_command, **repair_kwargs
                )
                self.shell(repair_command_prepared)
            else:
                shutil.move(str(built_wheel), repaired_wheel_dir)

        return tuple(self.venv.base.glob(repaired_wheel_dir, "*.whl"))

    def update_repair_kwargs(self, repair_kwargs: Dict[str, PathOrStr]) -> None:
        pass


def test_one(
    platform_backend: PlatformBackend,
    base_python: PurePath,
    constraints_dict: Dict[str, str],
    build_options: BuildOptions,
    repaired_wheel: PurePath,
    arch: Optional[str] = None,
) -> None:
    log.step("Testing wheel..." if arch is None else f"Testing wheel on {arch}...")
    with platform_backend.tmp_dir("test-venv") as venv_dir:
        venv = VirtualEnv(
            platform_backend, base_python, venv_dir, constraints_dict=constraints_dict, arch=arch
        )
        # update env with results from CIBW_ENVIRONMENT
        venv.env = build_options.environment.as_dictionary(
            prev_environment=venv.env, executor=platform_backend.environment_executor
        )
        # check that we are using the Python from the virtual environment
        # TODO venv.call("which", "python")

        prepare_kwargs = {
            "project": venv.base.get_remote_path(Path(".").resolve()),
            "package": venv.base.get_remote_path(build_options.package_dir.resolve()),
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
        venv.shell(test_command_prepared, cwd=venv.base.home)
