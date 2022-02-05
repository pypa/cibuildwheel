import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple, cast

from filelock import FileLock

from .architecture import Architecture
from .backend import BuilderBackend, do_test_wheel, run_before_all
from .logger import log
from .options import Options
from .platform_backend import NativePlatformBackend
from .typing import Literal, PathOrStr
from .util import (
    CIBW_CACHE_PATH,
    BuildSelector,
    call,
    detect_ci_provider,
    download,
    install_certifi_script,
    read_python_configs,
    unwrap,
)


def get_macos_version() -> Tuple[int, int]:
    """
    Returns the macOS major/minor version, as a tuple, e.g. (10, 15) or (11, 0)

    These tuples can be used in comparisons, e.g.
        (10, 14) <= (11, 0) == True
        (10, 14) <= (10, 16) == True
        (11, 2) <= (11, 0) != True
    """
    version_str, _, _ = platform.mac_ver()
    version = tuple(map(int, version_str.split(".")[:2]))
    return cast(Tuple[int, int], version)


def get_macos_sdks() -> List[str]:
    output = call("xcodebuild", "-showsdks", capture_stdout=True)
    return [m.group(1) for m in re.finditer(r"-sdk (macosx\S+)", output)]


class PythonConfiguration(NamedTuple):
    version: str
    identifier: str
    url: str


def get_python_configurations(
    build_selector: BuildSelector, architectures: Set[Architecture]
) -> List[PythonConfiguration]:

    full_python_configs = read_python_configs("macos")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    # filter out configs that don't match any of the selected architectures
    python_configurations = [
        c
        for c in python_configurations
        if any(c.identifier.endswith(a.value) for a in architectures)
    ]

    # skip builds as required by BUILD/SKIP
    return [c for c in python_configurations if build_selector(c.identifier)]


def install_cpython(tmp: Path, version: str, url: str) -> Path:
    installation_path = Path(f"/Library/Frameworks/Python.framework/Versions/{version}")
    with FileLock(CIBW_CACHE_PATH / f"cpython{version}.lock"):
        installed_system_packages = call("pkgutil", "--pkgs", capture_stdout=True).splitlines()
        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = f"org.python.Python.PythonFramework-{version}"
        if python_package_identifier not in installed_system_packages:
            if detect_ci_provider() is None:
                # if running locally, we don't want to install CPython with sudo
                # let the user know & provide a link to the installer
                print(
                    f"Error: CPython {version} is not installed.\n"
                    "cibuildwheel will not perform system-wide installs when running outside of CI.\n"
                    f"To build locally, install CPython {version} on this machine, or, disable this version of Python using CIBW_SKIP=cp{version.replace('.', '')}-macosx_*\n"
                    f"\nDownload link: {url}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            pkg_path = tmp / "Python.pkg"
            # download the pkg
            download(url, pkg_path)
            # install
            call("sudo", "installer", "-pkg", pkg_path, "-target", "/")
            pkg_path.unlink()
            env = os.environ.copy()
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
            call(installation_path / "bin" / "python3", install_certifi_script, env=env)

    return installation_path / "bin" / "python3"


def install_pypy(tmp: Path, version: str, url: str) -> Path:
    pypy_tar_bz2 = url.rsplit("/", 1)[-1]
    extension = ".tar.bz2"
    assert pypy_tar_bz2.endswith(extension)
    installation_path = CIBW_CACHE_PATH / pypy_tar_bz2[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            downloaded_tar_bz2 = tmp / pypy_tar_bz2
            download(url, downloaded_tar_bz2)
            installation_path.parent.mkdir(parents=True, exist_ok=True)
            call("tar", "-C", installation_path.parent, "-xf", downloaded_tar_bz2)
            downloaded_tar_bz2.unlink()
    return installation_path / "bin" / "pypy3"


def install_python(tmp: Path, python_configuration: PythonConfiguration) -> Path:
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        base_python = install_cpython(tmp, python_configuration.version, python_configuration.url)
    elif implementation_id.startswith("pp"):
        base_python = install_pypy(tmp, python_configuration.version, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")
    assert base_python.exists()
    return base_python


class _Builder(BuilderBackend):
    def get_extra_build_tools(self) -> Sequence[str]:
        return ["delocate"]

    def update_build_env(self, env: Dict[str, str]) -> None:
        # Set MACOSX_DEPLOYMENT_TARGET to 10.9, if the user didn't set it.
        # PyPy defaults to 10.7, causing inconsistencies if it's left unset.
        env.setdefault("MACOSX_DEPLOYMENT_TARGET", "10.9")

        config_is_arm64 = self.identifier.endswith("arm64")
        config_is_universal2 = self.identifier.endswith("universal2")

        if self.identifier[2:5] not in {"36-", "37-"}:
            if config_is_arm64:
                # macOS 11 is the first OS with arm64 support, so the wheels
                # have that as a minimum.
                env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-11.0-arm64")
                env.setdefault("ARCHFLAGS", "-arch arm64")
            elif config_is_universal2:
                env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-10.9-universal2")
                env.setdefault("ARCHFLAGS", "-arch arm64 -arch x86_64")
            elif self.identifier.endswith("x86_64"):
                # even on the macos11.0 Python installer, on the x86_64 side it's
                # compatible back to 10.9.
                env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-10.9-x86_64")
                env.setdefault("ARCHFLAGS", "-arch x86_64")

        building_arm64 = config_is_arm64 or config_is_universal2
        if building_arm64 and get_macos_version() < (10, 16) and "SDKROOT" not in env:
            # xcode 12.2 or higher can build arm64 on macos 10.15 or below, but
            # needs the correct SDK selected.
            sdks = get_macos_sdks()

            # Different versions of Xcode contain different SDK versions...
            # we're happy with anything newer than macOS 11.0
            arm64_compatible_sdks = [s for s in sdks if not s.startswith("macosx10.")]

            if not arm64_compatible_sdks:
                log.warning(
                    unwrap(
                        """
                        SDK for building arm64-compatible wheels not found. You need Xcode 12.2 or later
                        to build universal2 or arm64 wheels.
                        """
                    )
                )
            else:
                env.setdefault("SDKROOT", arm64_compatible_sdks[0])

    def update_repair_kwargs(self, repair_kwargs: Dict[str, PathOrStr]) -> None:
        if self.identifier.endswith("universal2"):
            repair_kwargs["delocate_archs"] = "x86_64,arm64"
        elif self.identifier.endswith("arm64"):
            repair_kwargs["delocate_archs"] = "arm64"
        else:
            repair_kwargs["delocate_archs"] = "x86_64"


def build_one(
    platform_backend: NativePlatformBackend,
    config: PythonConfiguration,
    options: Options,
) -> None:
    build_options = options.build_options(config.identifier)
    log.build_start(config.identifier)

    with platform_backend.tmp_dir("install") as install_tmp_dir:
        base_python = install_python(Path(install_tmp_dir), config)

    with platform_backend.tmp_dir("repaired_wheel") as repaired_wheel_dir:
        with _Builder(platform_backend, config.identifier, base_python, build_options) as builder:
            repaired_wheel = builder.run(repaired_wheel_dir)[0]
            constraints_dict = builder.constraints_dict

        if build_options.test_command and build_options.test_selector(config.identifier):
            machine_arch = platform.machine()
            testing_archs: List[Literal["x86_64", "arm64"]]

            config_is_arm64 = config.identifier.endswith("arm64")
            config_is_universal2 = config.identifier.endswith("universal2")

            if config_is_arm64:
                testing_archs = ["arm64"]
            elif config_is_universal2:
                testing_archs = ["x86_64", "arm64"]
            else:
                testing_archs = ["x86_64"]

            for testing_arch in testing_archs:
                if config_is_universal2:
                    arch_specific_identifier = f"{config.identifier}:{testing_arch}"
                    if not build_options.test_selector(arch_specific_identifier):
                        continue

                if machine_arch == "x86_64" and testing_arch == "arm64":
                    if config_is_arm64:
                        log.warning(
                            unwrap(
                                """
                                While arm64 wheels can be built on x86_64, they cannot be
                                tested. The ability to test the arm64 wheels will be added in a
                                future release of cibuildwheel, once Apple Silicon CI runners
                                are widely available. To silence this warning, set
                                `CIBW_TEST_SKIP: *-macosx_arm64`.
                                """
                            )
                        )
                    elif config_is_universal2:
                        log.warning(
                            unwrap(
                                """
                                While universal2 wheels can be built on x86_64, the arm64 part
                                of them cannot currently be tested. The ability to test the
                                arm64 part of a universal2 wheel will be added in a future
                                release of cibuildwheel, once Apple Silicon CI runners are
                                widely available. To silence this warning, set
                                `CIBW_TEST_SKIP: *-macosx_universal2:arm64`.
                                """
                            )
                        )
                    else:
                        raise RuntimeError("unreachable")

                    # skip this test
                    continue
                venv_arch: Optional[str] = None
                if testing_arch != machine_arch:
                    if machine_arch == "arm64" and testing_arch == "x86_64":
                        # rosetta2 will provide the emulation with just the arch prefix.
                        venv_arch = testing_arch
                    else:
                        raise RuntimeError(
                            "don't know how to emulate {testing_arch} on {machine_arch}"
                        )

                do_test_wheel(
                    platform_backend,
                    base_python,
                    constraints_dict,
                    build_options,
                    repaired_wheel,
                    arch=venv_arch,
                )

        # we're all done here; move it to output (overwrite existing)
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
        env = platform_backend.env.copy()
        env.setdefault("MACOSX_DEPLOYMENT_TARGET", "10.9")
        run_before_all(platform_backend, before_all_options, env)

        for config in python_configurations:
            build_one(platform_backend, config, options)

    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
