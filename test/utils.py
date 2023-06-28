"""
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
"""

import os
import platform as pm
import subprocess
import sys
from collections.abc import Mapping, Sequence
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
SINGLE_PYTHON_VERSION: Final[tuple[int, int]] = (3, 12)

_AARCH64_CAN_RUN_ARMV7: Final[bool] = Architecture.aarch64.value not in EMULATED_ARCHS and {
    None: Architecture.armv7l.value not in EMULATED_ARCHS,
    CIProvider.travis_ci: False,
    CIProvider.cirrus_ci: False,
}.get(detect_ci_provider(), True)

platform = os.environ.get("CIBW_PLATFORM", "")
if platform:
    pass
elif sys.platform.startswith("linux"):
    platform = "linux"
elif sys.platform.startswith("darwin"):
    platform = "macos"
elif sys.platform.startswith(("win32", "cygwin")):
    platform = "windows"
else:
    msg = f"Unsupported platform {sys.platform!r}"
    raise Exception(msg)


def cibuildwheel_get_build_identifiers(
    project_path: Path, env: dict[str, str] | None = None, *, prerelease_pythons: bool = False
) -> list[str]:
    """
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    """
    cmd = [sys.executable, "-m", "cibuildwheel", "--print-build-identifiers", str(project_path)]
    if env is None:
        env = os.environ.copy()
    env["CIBW_ENABLE"] = "cpython-freethreading pypy graalpy"
    if prerelease_pythons:
        env["CIBW_ENABLE"] += " cpython-prerelease"

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
    if platform == "linux":
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

    env["CIBW_ENABLE"] = " ".join(EnableGroup.all_groups())

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
    macosx_deployment_target: str = "10.9",
    machine_arch: str | None = None,
    python_abi_tags: list[str] | None = None,
    include_universal2: bool = False,
    single_python: bool = False,
    single_arch: bool = False,
) -> list[str]:
    """
    Returns a list of expected wheels from a run of cibuildwheel.
    """
    if machine_arch is None:
        machine_arch = pm.machine()
        if platform == "linux":
            machine_arch = arch_name_for_linux(machine_arch)

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

    wheels: list[str] = []
    for architecture in architectures:
        wheels.extend(
            _expected_wheels(
                package_name,
                package_version,
                architecture,
                manylinux_versions,
                musllinux_versions,
                macosx_deployment_target,
                python_abi_tags,
                include_universal2,
                single_python,
            )
        )
    return wheels


def _expected_wheels(
    package_name: str,
    package_version: str,
    machine_arch: str,
    manylinux_versions: list[str] | None,
    musllinux_versions: list[str] | None,
    macosx_deployment_target: str,
    python_abi_tags: list[str] | None,
    include_universal2: bool,
    single_python: bool,
) -> list[str]:
    """
    Returns a list of expected wheels from a run of cibuildwheel.
    """
    # per PEP 425 (https://www.python.org/dev/peps/pep-0425/), wheel files shall have name of the form
    # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    # {python tag} and {abi tag} are closely related to the python interpreter used to build the wheel
    # so we'll merge them below as python_abi_tag

    if manylinux_versions is None:
        manylinux_versions = {
            "armv7l": ["manylinux_2_17", "manylinux2014", "manylinux_2_31"],
            "i686": ["manylinux_2_5", "manylinux1", "manylinux_2_17", "manylinux2014"],
            "x86_64": ["manylinux_2_5", "manylinux1", "manylinux_2_28"],
        }.get(machine_arch, ["manylinux_2_17", "manylinux2014", "manylinux_2_28"])

    if musllinux_versions is None:
        musllinux_versions = ["musllinux_1_2"]

    if platform == "pyodide" and python_abi_tags is None:
        python_abi_tags = ["cp312-cp312"]
    if python_abi_tags is None:
        python_abi_tags = [
            "cp38-cp38",
            "cp39-cp39",
            "cp310-cp310",
            "cp311-cp311",
            "cp312-cp312",
            "cp313-cp313",
            "cp313-cp313t",
        ]

        if machine_arch in ["x86_64", "i686", "AMD64", "aarch64", "arm64"]:
            python_abi_tags += [
                "pp38-pypy38_pp73",
                "pp39-pypy39_pp73",
                "pp310-pypy310_pp73",
                "pp311-pypy311_pp73",
            ]
        if machine_arch in ["x86_64", "AMD64", "aarch64", "arm64"]:
            python_abi_tags += [
                "graalpy311-graalpy242_311_native",
            ]

    if single_python:
        python_tag = "cp{}{}-".format(*SINGLE_PYTHON_VERSION)
        python_abi_tags = [
            next(
                tag
                for tag in python_abi_tags
                if tag.startswith(python_tag) and not tag.endswith("t")
            )
        ]

    wheels = []

    if platform == "pyodide":
        assert len(python_abi_tags) == 1
        python_abi_tag = python_abi_tags[0]
        platform_tag = "pyodide_2024_0_wasm32"
        return [f"{package_name}-{package_version}-{python_abi_tag}-{platform_tag}.whl"]

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
            platform_tags = ["win_amd64"] if machine_arch == "AMD64" else ["win32"]

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
        else:
            msg = f"Unsupported platform {platform!r}"
            raise Exception(msg)

        for platform_tag in platform_tags:
            wheels.append(f"{package_name}-{package_version}-{python_abi_tag}-{platform_tag}.whl")

    return wheels


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
    return pytest.mark.skipif(platform == "pyodide", reason=reason)


def invoke_pytest() -> str:
    # see https://github.com/pyodide/pyodide/issues/4802
    if platform == "pyodide" and sys.platform.startswith("darwin"):
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
