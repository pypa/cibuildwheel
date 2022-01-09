import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PurePath
from typing import Dict, List, NamedTuple, Optional, Sequence, Set
from zipfile import ZipFile

from filelock import FileLock
from packaging.version import Version

from .architecture import Architecture
from .backend import BuilderBackend, test_one_base
from .environment import ParsedEnvironment
from .logger import log
from .options import BuildOptions, Options
from .platform_backend import NativePlatformBackend
from .typing import PathOrStr
from .util import (
    CIBW_CACHE_PATH,
    BuildSelector,
    DependencyConstraints,
    call,
    download,
    prepare_command,
    read_python_configs,
    shell,
)
from .virtualenv import VirtualEnv


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
    platform_backend: NativePlatformBackend,
    venv_path: Path,
    base_python: Path,
    identifier: str,
    dependency_constraints: Optional[DependencyConstraints],
    environment: ParsedEnvironment,
) -> VirtualEnv:
    log.step("Setting up build environment...")

    dependency_constraint_flags: Sequence[PathOrStr] = []
    constraints_path: Optional[Path] = None
    if dependency_constraints:
        constraints_path = dependency_constraints.get_for_identifier(identifier)
        dependency_constraint_flags = ["-c", constraints_path]

    venv = VirtualEnv(platform_backend, base_python, venv_path, constraints_path=constraints_path)

    # pip older than 21.3 builds executables such as pip.exe for x64 platform.
    # The first re-install of pip updates pip module but builds pip.exe using
    # the old pip which still generates x64 executable. But the second
    # re-install uses updated pip and correctly builds pip.exe for the target.
    # This can be removed once ARM64 Pythons (currently 3.9 and 3.10) bundle
    # pip versions newer than 21.3.
    if identifier.endswith("arm64") and venv.pip_version < Version("21.3"):
        venv.install("--force-reinstall", "pip", *dependency_constraint_flags)

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip.exe'
    venv.install("--upgrade", "pip", *dependency_constraint_flags)

    # update env with results from CIBW_ENVIRONMENT
    venv.env = environment.as_dictionary(prev_environment=venv.env)

    # check what Python version we're on
    venv.call("where", "python")
    venv.call("python", "--version")
    venv.call("python", "-c", "\"import struct; print(struct.calcsize('P') * 8)\"")
    where_python = venv.call("where", "python", capture_stdout=True).splitlines()[0].strip()
    if where_python != str(venv_path / "Scripts" / "python.exe"):
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # check what pip version we're on
    assert (venv_path / "Scripts" / "pip.exe").exists()
    where_pip = venv.call("where", "pip", capture_stdout=True).splitlines()[0].strip()
    if where_pip.strip() != str(venv_path / "Scripts" / "pip.exe"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    venv.call("pip", "--version")
    return venv


def test_one(
    platform_backend: NativePlatformBackend,
    base_python: Path,
    constraints_dict: Dict[str, str],
    build_options: BuildOptions,
    repaired_wheel: PurePath,
) -> None:
    with platform_backend.tmp_dir("test-venv") as venv_dir:
        venv = VirtualEnv(
            platform_backend, base_python, venv_dir, constraints_dict=constraints_dict
        )
        # update env with results from CIBW_ENVIRONMENT
        venv.env = build_options.environment.as_dictionary(prev_environment=venv.env)
        # check that we are using the Python from the virtual environment
        venv.call("where", "python")
        test_one_base(venv, build_options, repaired_wheel)


def build_one(
    platform_backend: NativePlatformBackend, config: PythonConfiguration, options: Options
) -> None:
    build_options = options.build_options(config.identifier)
    log.build_start(config.identifier)

    with platform_backend.tmp_dir("install") as install_tmp_dir:
        base_python = install_python(Path(install_tmp_dir), config)

    with platform_backend.tmp_dir("repaired_wheel") as repaired_wheel_dir:

        with platform_backend.tmp_dir("build") as build_tmp_dir:
            venv = setup_build_venv(
                platform_backend,
                Path(build_tmp_dir / "venv"),
                base_python,
                config.identifier,
                build_options.dependency_constraints,
                build_options.environment,
            )
            builder = BuilderBackend(build_options, venv, config.identifier)
            builder.install_build_tools([])
            repaired_wheel = builder.build(repaired_wheel_dir)
            constraints_dict = venv.constraints_dict

        if build_options.test_command and options.globals.test_selector(config.identifier):
            test_one(platform_backend, base_python, constraints_dict, build_options, repaired_wheel)

        # we're all done here; move it to output (remove if already exists)
        shutil.move(str(repaired_wheel), build_options.output_dir)

    log.build_end()


def build(options: Options, tmp_dir: Path) -> None:
    platform_backend = NativePlatformBackend(tmp_dir)
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
            build_one(platform_backend, config, options)

    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
