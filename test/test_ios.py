from __future__ import annotations

import os
import platform
import subprocess

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()
basic_project.files["tests/test_platform.py"] = f"""
import platform
from unittest import TestCase

class TestPlatform(TestCase):
    def test_platform(self):
        self.assertEqual(platform.machine(), "{platform.machine()}")

"""


# iOS tests shouldn't be run in parallel, because they're dependent on starting
# a simulator. It's *possible* to start multiple simulators, but not advisable
# to start as many simulators as there are CPUs on the test machine.
@pytest.mark.xdist_group(name="ios")
@pytest.mark.parametrize(
    "build_config",
    [
        # Default to the pip build frontend.
        {"CIBW_PLATFORM": "ios"},
        # Also check the build frontend
        {"CIBW_PLATFORM": "ios", "CIBW_BUILD_FRONTEND": "build"},
    ],
)
def test_ios_platforms(tmp_path, build_config):
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp313-*",
            "CIBW_TEST_SOURCES": "tests",
            "CIBW_TEST_COMMAND": "unittest discover tests test_platform.py",
            **build_config,
        },
    )

    ios_version = os.getenv("IPHONEOS_DEPLOYMENT_TARGET", "13.0").replace(".", "_")
    platform_machine = platform.machine()

    # Tests are only executed on simulator. The test suite passes if it's
    # running on the same architecture as the current platform.
    if platform_machine == "x86_64":
        expected_wheels = {
            f"spam-0.1.0-cp313-cp313-ios_{ios_version}_x86_64_iphonesimulator.whl",
        }

    elif platform_machine == "arm64":
        expected_wheels = {
            f"spam-0.1.0-cp313-cp313-ios_{ios_version}_arm64_iphoneos.whl",
            f"spam-0.1.0-cp313-cp313-ios_{ios_version}_arm64_iphonesimulator.whl",
        }

    assert set(actual_wheels) == expected_wheels


@pytest.mark.xdist_group(name="ios")
def test_no_test_sources(tmp_path, capfd):
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_PLATFORM": "ios",
                "CIBW_BUILD": "cp313-*",
                "CIBW_TEST_COMMAND": "tests",
            },
        )

    captured = capfd.readouterr()
    assert "Testing on iOS requires a definition of test-sources." in captured.err
