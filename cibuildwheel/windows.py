import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Set
from zipfile import ZipFile

from filelock import FileLock
from packaging.version import Version

from .architecture import Architecture
from .common import build_one_base, install_build_tools, test_one_base
from .environment import ParsedEnvironment
from .logger import log
from .options import BuildOptions, Options
from .typing import PathOrStr
from .util import (
    CIBW_CACHE_PATH,
    BuildFrontend,
    BuildSelector,
    DependencyConstraints,
    call,
    download,
    get_pip_version,
    new_tmp_dir,
    prepare_command,
    read_python_configs,
    shell,
    virtualenv,
)


def get_nuget_args(version: str, arch: str, output_directory: Path) -> List[str]:
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


class PythonConfiguration(NamedTuple):
    version: str
    arch: str
    identifier: str
    url: Optional[str] = None


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> List[PythonConfiguration]:

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


def install_python(tmp: Path, python_configuration: PythonConfiguration) -> Path:
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        base_python = install_cpython(python_configuration.version, python_configuration.arch)
    elif implementation_id.startswith("pp"):
        assert python_configuration.url is not None
        base_python = install_pypy(tmp, python_configuration.arch, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")
    assert base_python.exists()
    return base_python


def setup_build_venv(
    venv_path: Path,
    base_python: Path,
    identifier: str,
    python_version: str,
    dependency_constraints: Optional[DependencyConstraints],
    environment: ParsedEnvironment,
    build_frontend: BuildFrontend,
) -> Dict[str, str]:
    log.step("Setting up build environment...")

    dependency_constraint_flags: Sequence[PathOrStr] = []
    if dependency_constraints:
        dependency_constraint_flags = [
            "-c",
            dependency_constraints.get_for_python_version(python_version),
        ]

    env = virtualenv(base_python, venv_path, dependency_constraint_flags)

    # we version pip ourselves, so we don't care about pip version checking
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # pip older than 21.3 builds executables such as pip.exe for x64 platform.
    # The first re-install of pip updates pip module but builds pip.exe using
    # the old pip which still generates x64 executable. But the second
    # re-install uses updated pip and correctly builds pip.exe for the target.
    # This can be removed once ARM64 Pythons (currently 3.9 and 3.10) bundle
    # pip versions newer than 21.3.
    if identifier.endswith("arm64") and Version(get_pip_version(env)) < Version("21.3"):
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

    install_build_tools(build_frontend, [], env, dependency_constraint_flags)

    return env


def test_one(
    tmp_dir: Path, base_python: Path, build_options: BuildOptions, repaired_wheel: Path
) -> None:
    venv_dir = tmp_dir / "venv"
    env = virtualenv(base_python, venv_dir, [])
    # update env with results from CIBW_ENVIRONMENT
    env = build_options.environment.as_dictionary(prev_environment=env)
    # check that we are using the Python from the virtual environment
    call("where", "python", env=env)
    test_one_base(env, build_options, repaired_wheel)


def build_one(config: PythonConfiguration, options: Options, tmp_dir: Path) -> None:
    build_options = options.build_options(config.identifier)
    log.build_start(config.identifier)

    with new_tmp_dir(tmp_dir / "install") as install_tmp_dir:
        base_python = install_python(install_tmp_dir, config)

    repaired_wheel_dir = tmp_dir / "repaired_wheel"
    with new_tmp_dir(tmp_dir / "build") as build_tmp_dir:
        env = setup_build_venv(
            build_tmp_dir / "venv",
            base_python,
            config.identifier,
            config.version,
            build_options.dependency_constraints,
            build_options.environment,
            build_options.build_frontend,
        )
        repaired_wheel = build_one_base(
            tmp_dir, repaired_wheel_dir, env, config.identifier, config.version, build_options
        )

    if build_options.test_command and options.globals.test_selector(config.identifier):
        with new_tmp_dir(tmp_dir / "test") as test_tmp_dir:
            test_one(test_tmp_dir, base_python, build_options, repaired_wheel)

    # we're all done here; move it to output (remove if already exists)
    shutil.move(str(repaired_wheel), build_options.output_dir)

    log.build_end()


def build(options: Options, tmp_dir: Path) -> None:
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
                before_all_options.before_all, project=".", package=options.globals.package_dir
            )
            shell(before_all_prepared, env=env)

        for config in python_configurations:
            with new_tmp_dir(tmp_dir / config.identifier) as identifier_tmp_dir:
                build_one(config, options, identifier_tmp_dir)

    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
