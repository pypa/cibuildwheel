import shutil
from pathlib import Path
from typing import Dict, Iterable, Sequence

from .logger import log
from .options import BuildOptions
from .typing import PathOrStr, assert_never
from .util import (
    BuildFrontend,
    NonPlatformWheelError,
    call,
    get_build_verbosity_extra_flags,
    get_pip_version,
    prepare_command,
    shell,
)


def install_build_tools(
    build_frontend: BuildFrontend,
    extras: Iterable[str],
    env: Dict[str, str],
    dependency_constraint_flags: Sequence[PathOrStr],
) -> None:
    log.step("Installing build tools...")
    if build_frontend == "pip":
        tools = ["setuptools", "wheel"]
    elif build_frontend == "build":
        tools = ["build[virtualenv]"]
    else:
        assert_never(build_frontend)

    call("pip", "install", "--upgrade", *tools, *extras, *dependency_constraint_flags, env=env)


def build_one_base(
    tmp_dir: Path,
    repaired_wheel_dir: Path,
    env: Dict[str, str],
    identifier: str,
    python_version: str,
    build_options: BuildOptions,
) -> Path:
    built_wheel_dir = tmp_dir / "built_wheel"

    # run the before_build command
    if build_options.before_build:
        log.step("Running before_build...")
        before_build_prepared = prepare_command(
            build_options.before_build, project=".", package=build_options.package_dir
        )
        shell(before_build_prepared, env=env)

    log.step("Building wheel...")
    built_wheel_dir.mkdir()

    verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)

    if build_options.build_frontend == "pip":
        # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
        # see https://github.com/pypa/cibuildwheel/pull/369
        call(
            "python",
            "-m",
            "pip",
            "wheel",
            build_options.package_dir.resolve(),
            f"--wheel-dir={built_wheel_dir}",
            "--no-deps",
            *verbosity_flags,
            env=env,
        )
    elif build_options.build_frontend == "build":
        config_setting = " ".join(verbosity_flags)
        build_env = env.copy()
        if build_options.dependency_constraints:
            constraints_path = build_options.dependency_constraints.get_for_python_version(
                python_version
            )
            # Bug in pip <= 21.1.3 - we can't have a space in the
            # constraints file, and pip doesn't support drive letters
            # in uhi.  After probably pip 21.2, we can use uri. For
            # now, use a temporary file.
            if " " in str(constraints_path):
                assert " " not in str(tmp_dir)
                tmp_file = tmp_dir / "constraints.txt"
                tmp_file.write_bytes(constraints_path.read_bytes())
                constraints_path = tmp_file

            build_env["PIP_CONSTRAINT"] = str(constraints_path)
            build_env["VIRTUALENV_PIP"] = get_pip_version(env)
        call(
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
        if "macos" in identifier:
            if identifier.endswith("universal2"):
                repair_kwargs["delocate_archs"] = "x86_64,arm64"
            elif identifier.endswith("arm64"):
                repair_kwargs["delocate_archs"] = "arm64"
            else:
                repair_kwargs["delocate_archs"] = "x86_64"
        repair_command_prepared = prepare_command(build_options.repair_command, **repair_kwargs)
        shell(repair_command_prepared, env=env)
    else:
        shutil.move(str(built_wheel), repaired_wheel_dir)

    return next(repaired_wheel_dir.glob("*.whl"))
