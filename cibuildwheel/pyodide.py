from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Sequence, Set
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .options import Options
from .typing import PathOrStr
from .util import (
    CIBW_CACHE_PATH,
    AlreadyBuiltWheelError,
    BuildFrontendConfig,
    BuildSelector,
    NonPlatformWheelError,
    call,
    download,
    ensure_node,
    extract_zip,
    find_compatible_wheel,
    get_pip_version,
    prepare_command,
    read_python_configs,
    shell,
    split_config_settings,
    test_fail_cwd_file,
    virtualenv,
)


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    pyodide_version: str
    emscripten_version: str
    node_version: str


def install_emscripten(tmp: Path, version: str) -> Path:
    # We don't need to match the emsdk version to the version we install, but
    # we do for stability
    url = f"https://github.com/emscripten-core/emsdk/archive/refs/tags/{version}.zip"
    installation_path = CIBW_CACHE_PATH / f"emsdk-{version}"
    emsdk_path = installation_path / f"emsdk-{version}/emsdk"
    emcc_path = installation_path / f"emsdk-{version}/upstream/emscripten/emcc"
    with FileLock(f"{installation_path}.lock"):
        if installation_path.exists():
            return emcc_path
        emsdk_zip = tmp / "emsdk.zip"
        download(url, emsdk_zip)
        installation_path.mkdir()
        extract_zip(emsdk_zip, installation_path)
        call(emsdk_path, "install", version)
        call(emsdk_path, "activate", version)

    return emcc_path


def install_xbuildenv(env: dict[str, str], pyodide_version: str) -> str:
    pyodide_root = (
        CIBW_CACHE_PATH
        / f".pyodide-xbuildenv-{pyodide_version}/{pyodide_version}/xbuildenv/pyodide-root"
    )
    with FileLock(CIBW_CACHE_PATH / "xbuildenv.lock"):
        if pyodide_root.exists():
            return str(pyodide_root)

        # We don't want to mutate env but we need to delete any existing
        # PYODIDE_ROOT so copy it first.
        env = dict(env)
        env.pop("PYODIDE_ROOT", None)
        call(
            "pyodide",
            "xbuildenv",
            "install",
            pyodide_version,
            env=env,
            cwd=CIBW_CACHE_PATH,
        )
    return str(pyodide_root)


def get_base_python(identifier: str) -> Path:
    implementation_id = identifier.split("-")[0]
    majorminor = implementation_id[len("cp") :]
    major_minor = f"{majorminor[0]}.{majorminor[1:]}"
    python_name = f"python{major_minor}"
    which_python = shutil.which(python_name)
    if which_python is None:
        print(
            f"Error: CPython {major_minor} is not installed.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return Path(which_python)


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    dependency_constraint_flags: Sequence[PathOrStr],
    environment: ParsedEnvironment,
) -> dict[str, str]:
    base_python = get_base_python(python_configuration.identifier)

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(python_configuration.version, base_python, venv_path, [])
    venv_bin_path = venv_path / "bin"
    assert venv_bin_path.exists()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip'
    call(
        "python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        *dependency_constraint_flags,
        env=env,
        cwd=venv_path,
    )

    env = environment.as_dictionary(prev_environment=env)

    # check what pip version we're on
    assert (venv_bin_path / "pip").exists()
    call("which", "pip", env=env)
    call("pip", "--version", env=env)
    which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
    if which_pip != str(venv_bin_path / "pip"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our venv instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # check what Python version we're on
    call("which", "python", env=env)
    call("python", "--version", env=env)
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    if which_python != str(venv_bin_path / "python"):
        print(
            "cibuildwheel: python available on PATH doesn't match our venv instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    log.step("Installing build tools...")
    call(
        "pip",
        "install",
        "--upgrade",
        "auditwheel-emscripten",
        "build[virtualenv]",
        "pyodide-build",
        *dependency_constraint_flags,
        env=env,
    )

    log.step("Installing emscripten...")
    emcc_path = install_emscripten(tmp, python_configuration.emscripten_version)

    env["PATH"] = os.pathsep.join([str(emcc_path.parent), env["PATH"]])

    log.step("Installing Pyodide xbuildenv...")
    env["PYODIDE_ROOT"] = install_xbuildenv(env, python_configuration.pyodide_version)

    return env


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],  # noqa: ARG001
) -> list[PythonConfiguration]:
    full_python_configs = read_python_configs("pyodide")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]
    return python_configurations


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    if not python_configurations:
        return

    try:
        before_all_options_identifier = python_configurations[0].identifier
        before_all_options = options.build_options(before_all_options_identifier)

        if before_all_options.before_all:
            log.step("Running before_all...")
            env = before_all_options.environment.as_dictionary(prev_environment=os.environ)
            before_all_prepared = prepare_command(
                before_all_options.before_all, project=".", package=before_all_options.package_dir
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            build_frontend = build_options.build_frontend or BuildFrontendConfig("build")

            if build_frontend.name == "pip":
                print("The pyodide platform doesn't support pip frontend", file=sys.stderr)
                sys.exit(1)
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"
            identifier_tmp_dir.mkdir()
            built_wheel_dir.mkdir()
            repaired_wheel_dir.mkdir()

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if build_options.dependency_constraints:
                constraints_path = build_options.dependency_constraints.get_for_python_version(
                    config.version, variant="pyodide"
                )
                dependency_constraint_flags = ["-c", constraints_path]

            env = setup_python(
                identifier_tmp_dir / "build",
                config,
                dependency_constraint_flags,
                build_options.environment,
            )
            pip_version = get_pip_version(env)
            # The Pyodide command line runner mounts all directories in the host
            # filesystem into the Pyodide file system, except for the custom
            # file systems /dev, /lib, /proc, and /tmp. Mounting the mount
            # points for alternate file systems causes some mysterious failure
            # of the process (it just quits without any clear error).
            #
            # Because of this, by default Pyodide can't see anything under /tmp.
            # This environment variable tells it also to mount our temp
            # directory.
            oldmounts = ""
            extra_mounts = [str(identifier_tmp_dir)]
            if str(Path(".").resolve()).startswith("/tmp"):
                extra_mounts.append(str(Path(".").resolve()))

            if "_PYODIDE_EXTRA_MOUNTS" in env:
                oldmounts = env["_PYODIDE_EXTRA_MOUNTS"] + ":"
            env["_PYODIDE_EXTRA_MOUNTS"] = oldmounts + ":".join(extra_mounts)

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                log.step_end()
                print(
                    f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with {config.identifier}. Skipping build step..."
                )
                built_wheel = compatible_wheel
            else:
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build, project=".", package=build_options.package_dir
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")

                extra_flags = split_config_settings(build_options.config_settings, "build")
                extra_flags += build_frontend.args

                if not 0 <= build_options.build_verbosity < 2:
                    msg = f"build_verbosity {build_options.build_verbosity} is not supported for build frontend. Ignoring."
                    log.warning(msg)

                build_env = env.copy()
                if build_options.dependency_constraints:
                    our_constraints = str(constraints_path)
                    user_constraints = build_env.get("PIP_CONSTRAINT")
                    build_env["PIP_CONSTRAINT"] = " ".join(
                        c for c in [our_constraints, user_constraints] if c
                    )
                build_env["VIRTUALENV_PIP"] = pip_version
                call(
                    "pyodide",
                    "build",
                    build_options.package_dir,
                    f"--outdir={built_wheel_dir}",
                    *extra_flags,
                    env=build_env,
                )
                built_wheel = next(built_wheel_dir.glob("*.whl"))

                if built_wheel.name.endswith("none-any.whl"):
                    raise NonPlatformWheelError()

                if build_options.repair_command:
                    log.step("Repairing wheel...")

                    repair_command_prepared = prepare_command(
                        build_options.repair_command,
                        wheel=built_wheel,
                        dest_dir=repaired_wheel_dir,
                    )
                    shell(repair_command_prepared, env=env)
                else:
                    shutil.move(str(built_wheel), repaired_wheel_dir)

                repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise AlreadyBuiltWheelError(repaired_wheel.name)

            if build_options.test_command and build_options.test_selector(config.identifier):
                log.step("Testing wheel...")

                venv_dir = identifier_tmp_dir / "venv-test"
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.

                virtualenv_env = env.copy()
                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(ensure_node(config.node_version)),
                        virtualenv_env["PATH"],
                    ]
                )

                # pyodide venv uses virtualenv under the hood
                # use the pip embedded with virtualenv & disable network updates
                virtualenv_create_env = virtualenv_env.copy()
                virtualenv_create_env["VIRTUALENV_PIP"] = pip_version
                virtualenv_create_env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "1"

                call("pyodide", "venv", venv_dir, env=virtualenv_create_env)

                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(venv_dir / "bin"),
                        virtualenv_env["PATH"],
                    ]
                )
                virtualenv_env["VIRTUAL_ENV"] = str(venv_dir)

                # check that we are using the Python from the virtual environment
                call("which", "python", env=virtualenv_env)

                if build_options.before_test:
                    before_test_prepared = prepare_command(
                        build_options.before_test,
                        project=".",
                        package=build_options.package_dir,
                    )
                    shell(before_test_prepared, env=virtualenv_env)

                # install the wheel
                call(
                    "pip",
                    "install",
                    f"{repaired_wheel}{build_options.test_extras}",
                    env=virtualenv_env,
                )

                # test the wheel
                if build_options.test_requires:
                    call("pip", "install", *build_options.test_requires, env=virtualenv_env)

                # run the tests from a temp dir, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_command_prepared = prepare_command(
                    build_options.test_command,
                    project=Path(".").resolve(),
                    package=build_options.package_dir.resolve(),
                )

                test_cwd = identifier_tmp_dir / "test_cwd"
                test_cwd.mkdir(exist_ok=True)
                (test_cwd / "test_fail.py").write_text(test_fail_cwd_file.read_text())

                shell(test_command_prepared, cwd=test_cwd, env=virtualenv_env)

            # we're all done here; move it to output (overwrite existing)
            if compatible_wheel is None:
                build_options.output_dir.joinpath(repaired_wheel.name).unlink(missing_ok=True)

                shutil.move(str(repaired_wheel), build_options.output_dir)
                built_wheels.append(build_options.output_dir / repaired_wheel.name)
    finally:
        pass
