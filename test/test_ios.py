from __future__ import annotations

import os
import platform
import subprocess

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()
basic_project.files["tests/__init__.py"] = ""
basic_project.files["tests/__main__.py"] = r"""
import platform
import time

# Workaround for CPython#130294
for i in range(0, 5):
    time.sleep(1)
    print("Ensure logger is running...")

print("running tests on " + platform.machine())
"""


def get_xcode_version() -> tuple[int, int]:
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


# iOS tests can't be run in parallel, because they're dependent on starting a
# simulator. It's *possible* to start multiple simulators, but probably not
# advisable to start as many simulators as there are CPUs on the test machine.
# There's also an underlying issue with the testbed starting multiple simulators
# in parallel (https://github.com/python/cpython/issues/129200); even if that
# issue is resolved, it's probably desirable to *not* parallelize iOS tests.
@pytest.mark.xdist_group(name="ios")
@pytest.mark.parametrize(
    "build_config",
    [
        {"CIBW_PLATFORM": "ios"},
        {"CIBW_PLATFORM": "iphonesimulator"},
        {"CIBW_PLATFORM": "iphoneos"},
        # Also check the build frontend
        {"CIBW_PLATFORM": "iphonesimulator", "CIBW_BUILD_FRONTEND": "build"},
    ],
)
def test_ios_platforms(tmp_path, capfd, build_config):
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env=dict(
            CIBW_BUILD="cp313-*",
            CIBW_TEST_SOURCES="tests",
            CIBW_TEST_COMMAND="tests",
            **build_config,
        ),
    )

    captured = capfd.readouterr()

    platform_machine = platform.machine()
    # Tests are only executed on device
    if build_config["CIBW_PLATFORM"] != "iphoneos":
        if platform_machine == "x86_64":
            # Ensure that tests were run on arm64.
            assert "running tests on x86_64" in captured.out
        elif platform_machine == "arm64":
            # Ensure that tests were run on arm64.
            assert "running tests on arm64" in captured.out

    expected_wheels = set()
    ios_version = os.getenv("IPHONEOS_DEPLOYMENT_TARGET", "13.0").replace(".", "_")

    if build_config["CIBW_PLATFORM"] in {"ios", "iphoneos"}:
        expected_wheels.update(
            {
                f"spam-0.1.0-cp313-cp313-ios_{ios_version}_arm64_iphoneos.whl",
            }
        )

    if build_config["CIBW_PLATFORM"] in {"ios", "iphonesimulator"}:
        expected_wheels.update(
            {
                f"spam-0.1.0-cp313-cp313-ios_{ios_version}_arm64_iphonesimulator.whl",
                f"spam-0.1.0-cp313-cp313-ios_{ios_version}_x86_64_iphonesimulator.whl",
            }
        )

    assert set(actual_wheels) == expected_wheels
