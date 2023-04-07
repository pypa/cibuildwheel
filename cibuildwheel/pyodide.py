from __future__ import annotations

import contextlib
import os
import shutil
import sys
from collections.abc import Set
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from filelock import FileLock

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .options import Options
from .typing import PathOrStr
from .util import (
    CIBW_CACHE_PATH,
    BuildFrontend,
    BuildSelector,
    NonPlatformWheelError,
    call,
    download,
    extract_zip,
    find_compatible_wheel,
    get_build_verbosity_extra_flags,
    get_pip_version,
    prepare_command,
    pyodide_python_script,
    read_python_configs,
    resources_dir,
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


def install_emscripten(tmp: Path, version: str) -> Path:
    url = "https://github.com/emscripten-core/emsdk/archive/main.zip"
    installation_path = CIBW_CACHE_PATH / ("emsdk-" + version)
    emsdk_path = installation_path / "emsdk-main/emsdk"
    emcc_path = installation_path / "emsdk-main/upstream/emscripten/emcc"
    with FileLock(str(installation_path) + ".lock"):
        if installation_path.exists():
            return emcc_path
        emsdk_zip = tmp / "emsdk.zip"
        download(url, emsdk_zip)
        installation_path.mkdir()
        extract_zip(emsdk_zip, installation_path)
        os.chmod(emsdk_path, 0o777)
        call(emsdk_path, "install", version)
        call(emsdk_path, "activate", version)

    return emcc_path


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
    _build_frontend: BuildFrontend,
) -> dict[str, str]:
    pyodide_version = python_configuration.pyodide_version
    base_python = get_base_python(python_configuration.identifier)

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(base_python, venv_path, dependency_constraint_flags)
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
    if "HOME" not in env:
        # Workaround for https://github.com/pyodide/pyodide/pull/3744
        env["HOME"] = ""

    # check what pip version we're on
    assert (venv_bin_path / "pip").exists()
    call("which", "pip", env=env)
    call("pip", "--version", env=env)
    which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
    if which_pip != str(venv_bin_path / "pip"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # check what Python version we're on
    call("which", "python", env=env)
    call("python", "--version", env=env)
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    if which_python != str(venv_bin_path / "python"):
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
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
        f"pyodide-build=={pyodide_version}",
        *dependency_constraint_flags,
        env=env,
    )

    log.step("Installing emscripten...")
    emcc_path = install_emscripten(tmp, python_configuration.emscripten_version)

    env["PATH"] = os.pathsep.join([env["PATH"], str(emcc_path.parent)])

    # There will be a command to install the xbuildenv directly soon...
    # for now, pyodide config does it as a side effect.
    log.step("Installing Pyodide xbuildenv...")
    xbuildenv_cache_dir = CIBW_CACHE_PATH / (
        "pyodide-xbuildenv-" + python_configuration.pyodide_version
    )
    xbuildenv_cache_dir.mkdir(exist_ok=True)
    env.pop("PYODIDE_ROOT", None)
    stdout = call(
        "python",
        "-c",
        "from pyodide_build.out_of_tree.utils import initialize_pyodide_root ; "
        "import os ; "
        "initialize_pyodide_root() ; "
        'print("PYODIDE_ROOT:") ; '
        'print(os.environ["PYODIDE_ROOT"]) ;',
        env=env,
        cwd=xbuildenv_cache_dir,
        capture_stdout=True,
    )
    print(stdout)

    pyodide_root = xbuildenv_cache_dir / Path(stdout.split("\n")[-2])
    env["PYODIDE_ROOT"] = str(pyodide_root)

    pyodide_version_tuple = tuple(int(x) for x in pyodide_version.split("."))
    if pyodide_version_tuple < (0, 23, 1):
        shutil.copy(pyodide_python_script, pyodide_root / "dist/python")

    if pyodide_version_tuple == (0, 23, 0):
        # Oops we forgot this one...
        download(
            f"https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/python_stdlib.zip",
            pyodide_root / "dist/python_stdlib.zip",
        )

    env["_PYODIDE_EXTRA_MOUNTS"] = str(tmp)

    return env


def get_python_configurations(
    build_selector: BuildSelector, architectures: Set[Architecture]
) -> list[PythonConfiguration]:
    assert architectures == {Architecture.wasm32}
    full_python_configs = read_python_configs("pyodide")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]
    return python_configurations


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

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
            if build_options.build_frontend == "pip":
                print("Don't support pip frontend", file=sys.stderr)
                # sys.exit(1)
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if build_options.dependency_constraints:
                vesion_str = config.pyodide_version.rpartition(".")[0].replace(".", "_")
                constraints_path = resources_dir / f"constraints-pyodide-{vesion_str}.txt"
                dependency_constraint_flags = ["-c", constraints_path]

            env = setup_python(
                identifier_tmp_dir / "build",
                config,
                dependency_constraint_flags,
                build_options.environment,
                build_options.build_frontend,
            )

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
                built_wheel_dir.mkdir()

                verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
                extra_flags = split_config_settings(
                    build_options.config_settings, build_options.build_frontend
                )

                verbosity_setting = " ".join(verbosity_flags)
                extra_flags += (f"--config-setting={verbosity_setting}",)
                build_env = env.copy()
                if build_options.dependency_constraints:
                    build_env["PIP_CONSTRAINT"] = str(constraints_path)
                build_env["VIRTUALENV_PIP"] = get_pip_version(env)
                print("build_options.package_dir", build_options.package_dir)
                print(built_wheel_dir)
                call(
                    "pyodide",
                    "build",
                    build_options.package_dir,
                    *extra_flags,
                    env=build_env,
                    cwd=identifier_tmp_dir / "build",
                )
                output = next((identifier_tmp_dir / "build/dist").glob("*.whl"), None)
                if output is None:
                    output = next((build_options.package_dir / "dist").glob("*.whl"), None)

                shutil.move(str(output), built_wheel_dir)

                built_wheel = next(built_wheel_dir.glob("*.whl"))

                if built_wheel.name.endswith("none-any.whl"):
                    raise NonPlatformWheelError()

            if build_options.test_command and build_options.test_selector(config.identifier):
                log.step("Testing wheel...")

                venv_dir = identifier_tmp_dir / "venv-test"
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.

                # --no-download??
                call("pyodide", "venv", venv_dir, env=env)

                virtualenv_env = env.copy()
                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(venv_dir / "bin"),
                        virtualenv_env["PATH"],
                    ]
                )

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
                    f"{built_wheel}{build_options.test_extras}",
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
                with contextlib.suppress(FileNotFoundError):
                    (build_options.output_dir / built_wheel.name).unlink()

                shutil.move(str(built_wheel), build_options.output_dir)
                built_wheels.append(build_options.output_dir / built_wheel.name)
    finally:
        pass
