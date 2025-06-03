"""
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
"""

import os
import platform as pm
import subprocess
import sys
from collections.abc import Generator, Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Final

import pytest

from cibuildwheel.architecture import Architecture
from cibuildwheel.ci import CIProvider, detect_ci_provider
from cibuildwheel.selector import EnableGroup
from cibuildwheel.util.file import CIBW_CACHE_PATH

EMULATED_ARCHS: Final[list[str]] = sorted(
    arch.value for arch in (Architecture.all_archs("linux") - Architecture.auto_archs("linux"))
)
PYPY_ARCHS = ["x86_64", "i686", "AMD64", "aarch64", "arm64"]
GRAALPY_ARCHS = ["x86_64", "AMD64", "aarch64", "arm64"]

SINGLE_PYTHON_VERSION: Final[tuple[int, int]] = (3, 12)

_AARCH64_CAN_RUN_ARMV7: Final[bool] = Architecture.aarch64.value not in EMULATED_ARCHS and {
    None: Architecture.armv7l.value not in EMULATED_ARCHS,
    CIProvider.travis_ci: False,
    CIProvider.cirrus_ci: False,
}.get(detect_ci_provider(), True)


def get_platform() -> str:
    """Return the current platform as determined by CIBW_PLATFORM or sys.platform."""
    platform = os.environ.get("CIBW_PLATFORM", "")
    if platform:
        return platform
    elif sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform.startswith("darwin"):
        return "macos"
    elif sys.platform.startswith(("win32", "cygwin")):
        return "windows"
    else:
        msg = f"Unsupported platform {sys.platform!r}"
        raise Exception(msg)


DEFAULT_CIBW_ENABLE = "cpython-freethreading cpython-prerelease cpython-experimental-riscv64"


def get_enable_groups() -> frozenset[EnableGroup]:
    value = os.environ.get("CIBW_ENABLE", DEFAULT_CIBW_ENABLE)
    return EnableGroup.parse_option_value(value)


def cibuildwheel_get_build_identifiers(
    project_path: Path,
    env: dict[str, str] | None = None,
) -> list[str]:
    """
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    """
    cmd = [sys.executable, "-m", "cibuildwheel", "--print-build-identifiers", str(project_path)]
    if env is None:
        env = os.environ.copy()

    cmd_output = subprocess.run(
        cmd,
        text=True,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout

    return cmd_output.strip().split("\n")


def _update_pip_cache_dir(env: dict[str, str]) -> None:
    # Fix for pip concurrency bug https://github.com/pypa/pip/issues/11340
    # See https://github.com/pypa/cibuildwheel/issues/1254 for discussion.
    if get_platform() == "linux":
        return
    if "PIP_CACHE_DIR" in env:
        return
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is None or worker_id == "gw0":
        return
    pip_cache_dir = CIBW_CACHE_PATH / "test_cache" / f"pip_cache_dir_{worker_id}"
    env["PIP_CACHE_DIR"] = str(pip_cache_dir)


def cibuildwheel_run(
    project_path: str | Path,
    package_dir: str | Path = ".",
    env: dict[str, str] | None = None,
    add_env: Mapping[str, str] | None = None,
    output_dir: Path | None = None,
    add_args: Sequence[str] | None = None,
    single_python: bool = False,
) -> list[str]:
    """
    Runs cibuildwheel as a subprocess, building the project at project_path.

    Uses the current Python interpreter.

    :param project_path: path of the project to be built.
    :param package_dir: path of the package to be built. Can be absolute, or
    relative to project_path.
    :param env: full environment to be used, os.environ if None
    :param add_env: environment used to update env
    :param output_dir: directory where wheels are saved. If None, a temporary
    directory will be used for the duration of the command.
    :param add_args: Additional command-line arguments to pass to cibuildwheel.
    :return: list of built wheels (file names).
    """
    if env is None:
        env = os.environ.copy()
        # If present in the host environment, remove the MACOSX_DEPLOYMENT_TARGET for consistency
        env.pop("MACOSX_DEPLOYMENT_TARGET", None)

    if add_args is None:
        add_args = []

    if add_env is not None:
        env.update(add_env)

    _update_pip_cache_dir(env)

    if single_python:
        env["CIBW_BUILD"] = "cp{}{}-*".format(*SINGLE_PYTHON_VERSION)

    with TemporaryDirectory() as tmp_output_dir:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "cibuildwheel",
                "--output-dir",
                str(output_dir or tmp_output_dir),
                str(package_dir),
                *add_args,
            ],
            env=env,
            cwd=project_path,
            check=True,
        )
        wheels = [p.name for p in (output_dir or Path(tmp_output_dir)).iterdir()]
    return wheels


def _floor_macosx(*args: str) -> str:
    """
    Make sure a deployment target is not less than some value.
    """
    return max(args, key=lambda x: tuple(map(int, x.split("."))))


def expected_wheels(
    package_name: str,
    package_version: str,
    manylinux_versions: list[str] | None = None,
    musllinux_versions: list[str] | None = None,
    macosx_deployment_target: str | None = None,
    iphoneos_deployment_target: str | None = None,
    machine_arch: str | None = None,
    platform: str | None = None,
    python_abi_tags: list[str] | None = None,
    include_universal2: bool = False,
    single_python: bool = False,
    single_arch: bool = False,
) -> list[str]:
    """
    Returns the expected wheels from a run of cibuildwheel.
    """
    platform = platform or get_platform()

    if machine_arch is None:
        machine_arch = pm.machine()
        if platform == "linux":
            machine_arch = arch_name_for_linux(machine_arch)

    if macosx_deployment_target is None:
        macosx_deployment_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", "10.9")

    if iphoneos_deployment_target is None:
        iphoneos_deployment_target = os.environ.get("IPHONEOS_DEPLOYMENT_TARGET", "13.0")

    architectures = [machine_arch]
    if not single_arch:
        if platform == "linux":
            if machine_arch == "x86_64":
                architectures.append("i686")
            elif (
                machine_arch == "aarch64"
                and sys.platform.startswith("linux")
                and _AARCH64_CAN_RUN_ARMV7
            ):
                architectures.append("armv7l")
        elif platform == "windows" and machine_arch == "AMD64":
            architectures.append("x86")

    return [
        wheel
        for architecture in architectures
        for wheel in _expected_wheels(
            package_name=package_name,
            package_version=package_version,
            machine_arch=architecture,
            manylinux_versions=manylinux_versions,
            musllinux_versions=musllinux_versions,
            macosx_deployment_target=macosx_deployment_target,
            iphoneos_deployment_target=iphoneos_deployment_target,
            platform=platform,
            python_abi_tags=python_abi_tags,
            include_universal2=include_universal2,
            single_python=single_python,
        )
    ]


def _expected_wheels(
    package_name: str,
    package_version: str,
    machine_arch: str,
    manylinux_versions: list[str] | None,
    musllinux_versions: list[str] | None,
    macosx_deployment_target: str,
    iphoneos_deployment_target: str,
    platform: str,
    python_abi_tags: list[str] | None,
    include_universal2: bool,
    single_python: bool,
) -> Generator[str, None, None]:
    """
    Returns a list of expected wheels from a run of cibuildwheel.
    """
    # per PEP 425 (https://www.python.org/dev/peps/pep-0425/), wheel files shall have name of the form
    # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    # {python tag} and {abi tag} are closely related to the python interpreter used to build the wheel
    # so we'll merge them below as python_abi_tag

    enable_groups = EnableGroup.parse_option_value(os.environ.get("CIBW_ENABLE", ""))

    if manylinux_versions is None:
        manylinux_versions = {
            "armv7l": ["manylinux2014", "manylinux_2_17", "manylinux_2_31"],
            "i686": ["manylinux1", "manylinux2014", "manylinux_2_17", "manylinux_2_5"],
            "x86_64": ["manylinux1", "manylinux_2_28", "manylinux_2_5"],
            "riscv64": ["manylinux_2_31", "manylinux_2_35"],
        }.get(machine_arch, ["manylinux2014", "manylinux_2_17", "manylinux_2_28"])

    if musllinux_versions is None:
        musllinux_versions = ["musllinux_1_2"]

    if platform == "pyodide" and python_abi_tags is None:
        python_abi_tags = ["cp312-cp312"]
        if EnableGroup.PyodidePrerelease in enable_groups:
            python_abi_tags.append("cp313-cp313")
    elif platform == "ios" and python_abi_tags is None:
        python_abi_tags = ["cp313-cp313"]
    elif python_abi_tags is None:
        python_abi_tags = [
            "cp38-cp38",
            "cp39-cp39",
            "cp310-cp310",
            "cp311-cp311",
            "cp312-cp312",
            "cp313-cp313",
        ]

        enable_groups = get_enable_groups()
        if EnableGroup.CPythonFreeThreading in enable_groups:
            python_abi_tags.append("cp313-cp313t")

        if EnableGroup.CPythonPrerelease in enable_groups:
            python_abi_tags.append("cp314-cp314")
            if EnableGroup.CPythonFreeThreading in enable_groups:
                python_abi_tags.append("cp314-cp314t")

        if EnableGroup.PyPyEoL in enable_groups:
            python_abi_tags += [
                "pp38-pypy38_pp73",
                "pp39-pypy39_pp73",
            ]
        if EnableGroup.PyPy in enable_groups:
            python_abi_tags += [
                "pp310-pypy310_pp73",
                "pp311-pypy311_pp73",
            ]

        if EnableGroup.GraalPy in enable_groups:
            python_abi_tags += [
                "graalpy311-graalpy242_311_native",
            ]

    if machine_arch == "ARM64" and platform == "windows":
        # no CPython 3.8 on Windows ARM64
        python_abi_tags = [t for t in python_abi_tags if not t.startswith("cp38")]

    if machine_arch not in PYPY_ARCHS:
        python_abi_tags = [tag for tag in python_abi_tags if not tag.startswith("pp")]

    if machine_arch not in GRAALPY_ARCHS:
        python_abi_tags = [tag for tag in python_abi_tags if not tag.startswith("graalpy")]

    if single_python:
        python_tag = "cp{}{}-".format(*SINGLE_PYTHON_VERSION)
        python_abi_tags = [
            next(
                tag
                for tag in python_abi_tags
                if tag.startswith(python_tag) and not tag.endswith("t")
            )
        ]

    for python_abi_tag in python_abi_tags:
        platform_tags = []

        if platform == "linux":
            if len(manylinux_versions) > 0:
                platform_tags = [
                    ".".join(
                        f"{manylinux_version}_{machine_arch}"
                        for manylinux_version in manylinux_versions
                    )
                ]
            if len(musllinux_versions) > 0 and not python_abi_tag.startswith(("pp", "graalpy")):
                platform_tags.append(
                    ".".join(
                        f"{musllinux_version}_{machine_arch}"
                        for musllinux_version in musllinux_versions
                    )
                )

        elif platform == "windows":
            platform_tags = {
                "AMD64": ["win_amd64"],
                "ARM64": ["win_arm64"],
                "x86": ["win32"],
            }.get(machine_arch, [])

        elif platform == "macos":
            if python_abi_tag.startswith("pp"):
                if python_abi_tag.startswith("pp38"):
                    min_macosx = macosx_deployment_target
                else:
                    min_macosx = _floor_macosx(macosx_deployment_target, "10.15")
            elif python_abi_tag.startswith("cp"):
                if python_abi_tag.startswith(("cp38", "cp39", "cp310", "cp311")):
                    min_macosx = macosx_deployment_target
                else:
                    min_macosx = _floor_macosx(macosx_deployment_target, "10.13")
            else:
                min_macosx = macosx_deployment_target

            if machine_arch == "arm64":
                arm64_macosx = _floor_macosx(min_macosx, "11.0")
                platform_tags = [f"macosx_{arm64_macosx.replace('.', '_')}_arm64"]
            else:
                platform_tags = [f"macosx_{min_macosx.replace('.', '_')}_x86_64"]

            if include_universal2:
                platform_tags.append(f"macosx_{min_macosx.replace('.', '_')}_universal2")

        elif platform == "ios":
            if machine_arch == "x86_64":
                platform_tags = [
                    f"ios_{iphoneos_deployment_target.replace('.', '_')}_x86_64_iphonesimulator"
                ]
            elif machine_arch == "arm64":
                platform_tags = [
                    f"ios_{iphoneos_deployment_target.replace('.', '_')}_arm64_iphoneos",
                    f"ios_{iphoneos_deployment_target.replace('.', '_')}_arm64_iphonesimulator",
                ]
            else:
                msg = f"Unsupported architecture {machine_arch!r} for iOS"
                raise Exception(msg)

        elif platform == "pyodide":
            platform_tags = {
                "cp312-cp312": ["pyodide_2024_0_wasm32"],
                "cp313-cp313": ["pyodide_2025_0_wasm32"],
            }.get(python_abi_tag, [])

            if not platform_tags:
                # for example if the python tag is `none` or `abi3`, all
                # platform tags are built with that python tag
                platform_tags = ["pyodide_2024_0_wasm32"]

        else:
            msg = f"Unsupported platform {platform!r}"
            raise Exception(msg)

        for platform_tag in platform_tags:
            yield f"{package_name}-{package_version}-{python_abi_tag}-{platform_tag}.whl"


def get_macos_version() -> tuple[int, int]:
    """
    Returns the macOS major/minor version, as a tuple, e.g. (10, 15) or (11, 0)

    These tuples can be used in comparisons, e.g.
        (10, 14) <= (11, 0) == True
        (11, 2) <= (11, 0) != True
    """
    version_str, _, _ = pm.mac_ver()
    return tuple(map(int, version_str.split(".")[:2]))  # type: ignore[return-value]


def get_xcode_version() -> tuple[int, int]:
    """Calls `xcodebuild -version` to retrieve the Xcode version as a 2-tuple."""
    output = subprocess.run(
        ["xcodebuild", "-version"],
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    lines = output.splitlines()
    _, version_str = lines[0].split()

    version_parts = version_str.split(".")
    return (int(version_parts[0]), int(version_parts[1]))


def skip_if_pyodide(reason: str) -> Any:
    return pytest.mark.skipif(get_platform() == "pyodide", reason=reason)


def invoke_pytest() -> str:
    # see https://github.com/pyodide/pyodide/issues/4802
    if get_platform() == "pyodide":
        return "python -m pytest"
    return "pytest"


def arch_name_for_linux(arch: str) -> str:
    """
    Archs have different names on different platforms, but it's useful to be
    able to run linux tests on dev machines. This function translates between
    the different names.
    """
    if arch == "arm64":
        return "aarch64"
    return arch
