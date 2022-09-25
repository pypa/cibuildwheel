from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence
from zipfile import ZipFile

from filelock import FileLock
from packaging.version import Version

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .options import Options
from .typing import PathOrStr, assert_never
from .util import (
    CIBW_CACHE_PATH,
    AlreadyBuiltWheelError,
    BuildFrontend,
    BuildSelector,
    NonPlatformWheelError,
    call,
    download,
    find_compatible_wheel,
    get_build_verbosity_extra_flags,
    get_pip_version,
    prepare_command,
    read_python_configs,
    shell,
    split_config_settings,
    virtualenv,
)


def get_nuget_args(version: str, arch: str, output_directory: Path) -> list[str]:
    platform_suffix = {"32": "x86", "64": "", "ARM64": "arm64"}
    python_name = "python" + platform_suffix[arch]
    return [
        python_name,
        "-Version",
        version,
        "-FallbackSource",
        "https://api.nuget.org/v3/index.json",
        "-OutputDirectory",
        str(output_directory),
    ]


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    arch: str
    identifier: str
    url: str | None = None


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: set[Architecture],
) -> list[PythonConfiguration]:

    full_python_configs = read_python_configs("windows")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    map_arch = {"32": Architecture.x86, "64": Architecture.AMD64, "ARM64": Architecture.ARM64}

    # skip builds as required
    python_configurations = [
        c
        for c in python_configurations
        if build_selector(c.identifier) and map_arch[c.arch] in architectures
    ]

    return python_configurations


def extract_zip(zip_src: Path, dest: Path) -> None:
    with ZipFile(zip_src) as zip_:
        zip_.extractall(dest)


@lru_cache(maxsize=None)
def _ensure_nuget() -> Path:
    nuget = CIBW_CACHE_PATH / "nuget.exe"
    with FileLock(str(nuget) + ".lock"):
        if not nuget.exists():
            download("https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", nuget)
    return nuget


def install_cpython(version: str, arch: str) -> Path:
    base_output_dir = CIBW_CACHE_PATH / "nuget-cpython"
    nuget_args = get_nuget_args(version, arch, base_output_dir)
    installation_path = base_output_dir / (nuget_args[0] + "." + version) / "tools"
    with FileLock(str(base_output_dir) + f"-{version}-{arch}.lock"):
        if not installation_path.exists():
            nuget = _ensure_nuget()
            call(nuget, "install", *nuget_args)
    return installation_path / "python.exe"


def install_pypy(tmp: Path, arch: str, url: str) -> Path:
    assert arch == "64" and "win64" in url
    # Inside the PyPy zip file is a directory with the same name
    zip_filename = url.rsplit("/", 1)[-1]
    extension = ".zip"
    assert zip_filename.endswith(extension)
    installation_path = CIBW_CACHE_PATH / zip_filename[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            pypy_zip = tmp / zip_filename
            download(url, pypy_zip)
            # Extract to the parent directory because the zip file still contains a directory
            extract_zip(pypy_zip, installation_path.parent)
    return installation_path / "python.exe"


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    dependency_constraint_flags: Sequence[PathOrStr],
    environment: ParsedEnvironment,
    build_frontend: BuildFrontend,
) -> dict[str, str]:
    tmp.mkdir()
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        base_python = install_cpython(python_configuration.version, python_configuration.arch)
    elif implementation_id.startswith("pp"):
        assert python_configuration.url is not None
        base_python = install_pypy(tmp, python_configuration.arch, python_configuration.url)
    else:
        msg = "Unknown Python implementation"
        raise ValueError(msg)
    assert base_python.exists()

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(base_python, venv_path, dependency_constraint_flags)

    # set up environment variables for run_with_env
    env["PYTHON_VERSION"] = python_configuration.version
    env["PYTHON_ARCH"] = python_configuration.arch
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # pip older than 21.3 builds executables such as pip.exe for x64 platform.
    # The first re-install of pip updates pip module but builds pip.exe using
    # the old pip which still generates x64 executable. But the second
    # re-install uses updated pip and correctly builds pip.exe for the target.
    # This can be removed once ARM64 Pythons (currently 3.9 and 3.10) bundle
    # pip versions newer than 21.3.
    if python_configuration.arch == "ARM64" and Version(get_pip_version(env)) < Version("21.3"):
        call(
            "python",
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--upgrade",
            "pip",
            *dependency_constraint_flags,
            env=env,
            cwd=venv_path,
        )

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip.exe'
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

    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # check what Python version we're on
    call("where", "python", env=env)
    call("python", "--version", env=env)
    call("python", "-c", "\"import struct; print(struct.calcsize('P') * 8)\"", env=env)
    where_python = call("where", "python", env=env, capture_stdout=True).splitlines()[0].strip()
    if where_python != str(venv_path / "Scripts" / "python.exe"):
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # check what pip version we're on
    assert (venv_path / "Scripts" / "pip.exe").exists()
    where_pip = call("where", "pip", env=env, capture_stdout=True).splitlines()[0].strip()
    if where_pip.strip() != str(venv_path / "Scripts" / "pip.exe"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    call("pip", "--version", env=env)

    log.step("Installing build tools...")
    if build_frontend == "pip":
        call(
            "pip",
            "install",
            "--upgrade",
            "setuptools",
            "wheel",
            *dependency_constraint_flags,
            env=env,
        )
    elif build_frontend == "build":
        call(
            "pip",
            "install",
            "--upgrade",
            "build[virtualenv]",
            *dependency_constraint_flags,
            env=env,
        )
    else:
        assert_never(build_frontend)

    return env


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    if len(python_configurations) == 0:
        return

    try:
        before_all_options_identifier = python_configurations[0].identifier
        before_all_options = options.build_options(before_all_options_identifier)

        if before_all_options.before_all:
            log.step("Running before_all...")
            env = before_all_options.environment.as_dictionary(prev_environment=os.environ)
            before_all_prepared = prepare_command(
                before_all_options.before_all, project=".", package=options.globals.package_dir
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if build_options.dependency_constraints:
                dependency_constraint_flags = [
                    "-c",
                    build_options.dependency_constraints.get_for_python_version(config.version),
                ]

            # install Python
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
                repaired_wheel = compatible_wheel
            else:
                # run the before_build command
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build, project=".", package=options.globals.package_dir
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")
                built_wheel_dir.mkdir()

                verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
                extra_flags = split_config_settings(build_options.config_settings)

                if build_options.build_frontend == "pip":
                    extra_flags += verbosity_flags
                    # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                    # see https://github.com/pypa/cibuildwheel/pull/369
                    call(
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        options.globals.package_dir.resolve(),
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *extra_flags,
                        env=env,
                    )
                elif build_options.build_frontend == "build":
                    verbosity_setting = " ".join(verbosity_flags)
                    extra_flags += (f"--config-setting={verbosity_setting}",)
                    build_env = env.copy()
                    if build_options.dependency_constraints:
                        constraints_path = (
                            build_options.dependency_constraints.get_for_python_version(
                                config.version
                            )
                        )
                        # Bug in pip <= 21.1.3 - we can't have a space in the
                        # constraints file, and pip doesn't support drive letters
                        # in uhi.  After probably pip 21.2, we can use uri. For
                        # now, use a temporary file.
                        if " " in str(constraints_path):
                            assert " " not in str(identifier_tmp_dir)
                            tmp_file = identifier_tmp_dir / "constraints.txt"
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
                            *extra_flags,
                            env=build_env,
                        )
                else:
                    assert_never(build_options.build_frontend)

                built_wheel = next(built_wheel_dir.glob("*.whl"))

                # repair the wheel
                repaired_wheel_dir.mkdir()

                if built_wheel.name.endswith("none-any.whl"):
                    raise NonPlatformWheelError()

                if build_options.repair_command:
                    log.step("Repairing wheel...")
                    repair_command_prepared = prepare_command(
                        build_options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir
                    )
                    shell(repair_command_prepared, env=env)
                else:
                    shutil.move(str(built_wheel), repaired_wheel_dir)

                repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise AlreadyBuiltWheelError(repaired_wheel.name)

            if build_options.test_command and options.globals.test_selector(config.identifier):
                log.step("Testing wheel...")
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.
                call("pip", "install", "virtualenv", *dependency_constraint_flags, env=env)
                venv_dir = identifier_tmp_dir / "venv-test"

                # Use --no-download to ensure determinism by using seed libraries
                # built into virtualenv
                call("python", "-m", "virtualenv", "--no-download", venv_dir, env=env)

                virtualenv_env = env.copy()
                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(venv_dir / "Scripts"),
                        virtualenv_env["PATH"],
                    ]
                )

                # check that we are using the Python from the virtual environment
                call("where", "python", env=virtualenv_env)

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
                    str(repaired_wheel) + build_options.test_extras,
                    env=virtualenv_env,
                )

                # test the wheel
                if build_options.test_requires:
                    call("pip", "install", *build_options.test_requires, env=virtualenv_env)

                # run the tests from c:\, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_command_prepared = prepare_command(
                    build_options.test_command,
                    project=Path(".").resolve(),
                    package=options.globals.package_dir.resolve(),
                )
                shell(test_command_prepared, cwd="c:\\", env=virtualenv_env)

            # we're all done here; move it to output (remove if already exists)
            if compatible_wheel is None:
                shutil.move(str(repaired_wheel), build_options.output_dir)
                built_wheels.append(build_options.output_dir / repaired_wheel.name)

            # clean up
            # (we ignore errors because occasionally Windows fails to unlink a file and we
            # don't want to abort a build because of that)
            shutil.rmtree(identifier_tmp_dir, ignore_errors=True)

            log.build_end()
    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
