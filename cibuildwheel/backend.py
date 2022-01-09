import shutil
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

from .logger import log
from .options import BuildOptions
from .typing import PathOrStr, assert_never
from .util import (
    NonPlatformWheelError,
    get_build_verbosity_extra_flags,
    prepare_command,
)
from .virtualenv import VirtualEnv


class BuilderBackend:
    BUILD_TOOLS = {
        "pip": ["setuptools", "wheel"],
        "build": ["build[virtualenv]"],
    }

    def __init__(
        self, tmp_dir: Path, build_options: BuildOptions, venv: VirtualEnv, identifier: str
    ):
        self.tmp_dir = tmp_dir
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
            constraints_path = dependency_constraints.get_for_identifier(self.identifier)
            dependency_constraints_flags = ["-c", constraints_path]
        self.venv.install("--upgrade", *tools, *extras, *dependency_constraints_flags)

    def build(self, repaired_wheel_dir: Path) -> Path:
        build_options = self.build_options

        # run the before_build command
        if build_options.before_build:
            log.step("Running before_build...")
            before_build_prepared = prepare_command(
                build_options.before_build, project=".", package=build_options.package_dir
            )
            self.shell(before_build_prepared)

        log.step("Building wheel...")
        built_wheel_dir = self.tmp_dir / "built_wheel"
        built_wheel_dir.mkdir()
        verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
        if build_options.build_frontend == "pip":
            # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
            # see https://github.com/pypa/cibuildwheel/pull/369
            self.call(
                "python",
                "-m",
                "pip",
                "wheel",
                build_options.package_dir.resolve(),
                f"--wheel-dir={built_wheel_dir}",
                "--no-deps",
                *verbosity_flags,
            )
        elif build_options.build_frontend == "build":
            config_setting = " ".join(verbosity_flags)
            build_env = self.venv.env.copy()
            if build_options.dependency_constraints:
                constraints_path = build_options.dependency_constraints.get_for_identifier(
                    self.identifier
                )
                # Bug in pip <= 21.1.3 - we can't have a space in the
                # constraints file, and pip doesn't support drive letters
                # in uhi.  After probably pip 21.2, we can use uri. For
                # now, use a temporary file.
                if " " in str(constraints_path):
                    assert " " not in str(self.tmp_dir)
                    tmp_file = self.tmp_dir / "constraints.txt"
                    tmp_file.write_bytes(constraints_path.read_bytes())
                    constraints_path = tmp_file

                build_env["PIP_CONSTRAINT"] = str(constraints_path)
                build_env["VIRTUALENV_PIP"] = str(self.venv.pip_version)
            self.call(
                "python",
                "-m",
                "build",
                build_options.package_dir,
                "--wheel",
                f"--outdir={built_wheel_dir}",
                f"--config-setting={config_setting}",
                env=build_env,
            )
        else:
            assert_never(build_options.build_frontend)

        built_wheel = next(built_wheel_dir.glob("*.whl"))
        if built_wheel.name.endswith("none-any.whl"):
            raise NonPlatformWheelError()

        # repair the wheel
        repaired_wheel_dir.mkdir()
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
            shutil.move(str(built_wheel), repaired_wheel_dir)

        return next(repaired_wheel_dir.glob("*.whl"))

    def update_repair_kwargs(self, repair_kwargs: Dict[str, PathOrStr]) -> None:
        pass


def test_one_base(venv: VirtualEnv, build_options: BuildOptions, repaired_wheel: Path) -> None:
    log.step("Testing wheel..." if venv.arch is None else f"Testing wheel on {venv.arch}...")

    if build_options.before_test:
        before_test_prepared = prepare_command(
            build_options.before_test,
            project=".",
            package=build_options.package_dir,
        )
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
    test_command_prepared = prepare_command(
        build_options.test_command,
        project=Path(".").resolve(),
        package=build_options.package_dir.resolve(),
    )
    venv.shell(test_command_prepared, cwd=Path.home())
