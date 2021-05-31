"""
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
"""

import os
import platform as pm
import subprocess
import sys
from tempfile import TemporaryDirectory

platform: str

if "CIBW_PLATFORM" in os.environ:
    platform = os.environ["CIBW_PLATFORM"]
elif sys.platform.startswith("linux"):
    platform = "linux"
elif sys.platform.startswith("darwin"):
    platform = "macos"
elif sys.platform in ["win32", "cygwin"]:
    platform = "windows"
else:
    raise Exception("Unsupported platform")


def cibuildwheel_get_build_identifiers(project_path, env=None, *, prerelease_pythons=False):
    """
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    """
    cmd = [sys.executable, "-m", "cibuildwheel", "--print-build-identifiers", str(project_path)]
    if prerelease_pythons:
        cmd.append("--prerelease-pythons")

    cmd_output = subprocess.run(
        cmd,
        universal_newlines=True,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout

    return cmd_output.strip().split("\n")


def cibuildwheel_run(project_path, package_dir=".", env=None, add_env=None, output_dir=None):
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
    :return: list of built wheels (file names).
    """
    if env is None:
        env = os.environ.copy()
        # If present in the host environment, remove the MACOSX_DEPLOYMENT_TARGET for consistency
        env.pop("MACOSX_DEPLOYMENT_TARGET", None)

    if add_env is not None:
        env.update(add_env)

    with TemporaryDirectory() as tmp_output_dir:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "cibuildwheel",
                "--prerelease-pythons",
                "--output-dir",
                str(output_dir or tmp_output_dir),
                str(package_dir),
            ],
            env=env,
            cwd=project_path,
            check=True,
        )
        wheels = os.listdir(output_dir or tmp_output_dir)
    return wheels


def _get_arm64_macosx_deployment_target(macosx_deployment_target: str) -> str:
    """
    The first version of macOS that supports arm is 11.0. So the wheel tag
    cannot contain an earlier deployment target, even if
    MACOSX_DEPLOYMENT_TARGET sets it.
    """
    version_tuple = tuple(map(int, macosx_deployment_target.split(".")))
    if version_tuple <= (11, 0):
        return "11.0"
    else:
        return macosx_deployment_target


def expected_wheels(
    package_name,
    package_version,
    manylinux_versions=None,
    macosx_deployment_target="10.9",
    machine_arch=None,
):
    """
    Returns a list of expected wheels from a run of cibuildwheel.
    """
    # per PEP 425 (https://www.python.org/dev/peps/pep-0425/), wheel files shall have name of the form
    # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    # {python tag} and {abi tag} are closely related to the python interpreter used to build the wheel
    # so we'll merge them below as python_abi_tag

    if machine_arch is None:
        machine_arch = pm.machine()

    if manylinux_versions is None:
        if machine_arch == "x86_64":
            manylinux_versions = ["manylinux_2_5", "manylinux1", "manylinux_2_12", "manylinux2010"]
        else:
            manylinux_versions = ["manylinux_2_17", "manylinux2014"]

    python_abi_tags = ["cp36-cp36m", "cp37-cp37m", "cp38-cp38", "cp39-cp39", "cp310-cp310"]

    if machine_arch in ["x86_64", "AMD64", "x86", "aarch64"]:
        python_abi_tags += ["pp37-pypy37_pp73"]

    if platform == "macos" and get_macos_version() >= (10, 16):
        # 10.16 is sometimes reported as the macOS version on macOS 11.
        # pypy not supported on macOS 11.
        python_abi_tags = [t for t in python_abi_tags if not t.startswith("pp")]

    if platform == "macos" and machine_arch == "arm64":
        # currently, arm64 macs are only supported by cp39 & cp310
        python_abi_tags = ["cp39-cp39", "cp310-cp310"]

    wheels = []

    for python_abi_tag in python_abi_tags:
        platform_tags = []

        if platform == "linux":
            architectures = [machine_arch]

            if machine_arch == "x86_64":
                architectures.append("i686")

            platform_tags = [
                ".".join(
                    f"{manylinux_version}_{architecture}"
                    for manylinux_version in manylinux_versions
                )
                for architecture in architectures
            ]

        elif platform == "windows":
            if python_abi_tag.startswith("cp"):
                platform_tags = ["win32", "win_amd64"]
            else:
                platform_tags = ["win_amd64"]

        elif platform == "macos":
            if python_abi_tag == "cp39-cp39" and machine_arch == "arm64":
                arm64_macosx_deployment_target = _get_arm64_macosx_deployment_target(
                    macosx_deployment_target
                )
                platform_tags = [
                    f'macosx_{macosx_deployment_target.replace(".", "_")}_universal2',
                    f'macosx_{arm64_macosx_deployment_target.replace(".", "_")}_arm64',
                ]
            else:
                platform_tags = [
                    f'macosx_{macosx_deployment_target.replace(".", "_")}_x86_64',
                ]

        else:
            raise Exception("unsupported platform")

        for platform_tag in platform_tags:
            wheels.append(f"{package_name}-{package_version}-{python_abi_tag}-{platform_tag}.whl")

    return wheels


def get_macos_version():
    """
    Returns the macOS major/minor version, as a tuple, e.g. (10, 15) or (11, 0)

    These tuples can be used in comparisons, e.g.
        (10, 14) <= (11, 0) == True
        (11, 2) <= (11, 0) != True
    """
    version_str, _, _ = pm.mac_ver()
    return tuple(map(int, version_str.split(".")[:2]))
