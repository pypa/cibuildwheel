from __future__ import annotations

import os
import platform
import shutil
import subprocess

import pytest

from . import test_projects, utils

basic_project_files = {
    "tests/test_platform.py": f"""
import platform
from unittest import TestCase

class TestPlatform(TestCase):
    def test_platform(self):
        self.assertEqual(platform.machine(), "{platform.machine()}")

"""
}


# iOS tests shouldn't be run in parallel, because they're dependent on calling
# Xcode, and starting a simulator. These are both multi-threaded operations, and
# it's easy to overload the CI machine if there are multiple test processes
# running multithreaded processes. Therefore, they're put in the serial group,
# which is guaranteed to run single-process.
@pytest.mark.serial
@pytest.mark.parametrize(
    "build_config",
    [
        # Default to the pip build frontend
        {"CIBW_PLATFORM": "ios"},
        # Also check the build frontend
        {"CIBW_PLATFORM": "ios", "CIBW_BUILD_FRONTEND": "build"},
    ],
)
def test_ios_platforms(tmp_path, build_config, monkeypatch, capfd):
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    # Create a temporary "bin" directory, symlink a tool that we know eixsts
    # (/usr/bin/true) into that location under a name that should be unique,
    # and add the temp bin directory to the PATH.
    tools_dir = tmp_path / "bin"
    tools_dir.mkdir()
    tools_dir.joinpath("does-exist").symlink_to(shutil.which("true"))

    monkeypatch.setenv("PATH", str(tools_dir), prepend=os.pathsep)

    # Generate a test project that has an additional before-build step using the
    # known-to-exist tool.
    project_dir = tmp_path / "project"
    setup_py_add = "import subprocess\nsubprocess.run('does-exist', check=True)\n"
    basic_project = test_projects.new_c_project(setup_py_add=setup_py_add)
    basic_project.files.update(basic_project_files)
    basic_project.generate(project_dir)

    # Build and test the wheels. Mark the "does-exist" tool as a cross-build
    # tool, and invoke it during a `before-build` step. It will also be invoked
    # when `setup.py` is invoked.
    #
    # Tests are only executed on simulator. The test suite passes if it's
    # running on the same architecture as the current platform.
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BEFORE_BUILD": "does-exist",
            "CIBW_BUILD": "cp313-*",
            "CIBW_XBUILD_TOOLS": "does-exist",
            "CIBW_TEST_SOURCES": "tests",
            "CIBW_TEST_COMMAND": "unittest discover tests test_platform.py",
            "CIBW_BUILD_VERBOSITY": "1",
            **build_config,
        },
    )

    # The expected wheels were produced.
    ios_version = os.getenv("IPHONEOS_DEPLOYMENT_TARGET", "13.0").replace(".", "_")
    platform_machine = platform.machine()

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

    # The user was notified that the cross-build tool was found.
    captured = capfd.readouterr()
    assert "'does-exist' will be included in the cross-build environment" in captured.out


def test_no_test_sources(tmp_path, capfd):
    """Build will fail if test-sources isn't defined."""
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files.update(basic_project_files)
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

    # The error message indicates the configuration issue.
    captured = capfd.readouterr()
    assert "Testing on iOS requires a definition of test-sources." in captured.err


def test_missing_xbuild_tool(tmp_path, capfd):
    """Build will fail if xbuild-tools references a non-existent tool."""
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files.update(basic_project_files)
    basic_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_PLATFORM": "ios",
                "CIBW_BUILD": "cp313-*",
                "CIBW_TEST_COMMAND": "tests",
                "CIBW_XBUILD_TOOLS": "does-not-exist",
            },
        )

    # The error message indicates the problem tool.
    captured = capfd.readouterr()
    assert "Could not find a 'does-not-exist' executable on the path." in captured.err


def test_no_xbuild_tool_definition(tmp_path, capfd):
    """Build will succeed with a warning if there is no xbuild-tools definition."""
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files.update(basic_project_files)
    basic_project.generate(project_dir)

    # Build, but don't test the wheels; we're only checking that the right
    # warning was raised.
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_PLATFORM": "ios",
            "CIBW_BUILD": "cp313-*",
            "CIBW_TEST_SKIP": "*",
        },
    )

    # The expected wheels were produced.
    ios_version = os.getenv("IPHONEOS_DEPLOYMENT_TARGET", "13.0").replace(".", "_")
    platform_machine = platform.machine()

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

    # The user was notified that there was no cross-build tool definition.
    captured = capfd.readouterr()
    assert "Your project configuration does not define any cross-build tools." in captured.err


def test_empty_xbuild_tool_definition(tmp_path, capfd):
    """Build will succeed with no warning if there is an empty xbuild-tools definition."""
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files.update(basic_project_files)
    basic_project.generate(project_dir)

    # Build, but don't test the wheels; we're only checking that a warning
    # wasn't raised.
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_PLATFORM": "ios",
            "CIBW_BUILD": "cp313-*",
            "CIBW_TEST_SKIP": "*",
            "CIBW_XBUILD_TOOLS": "",
        },
    )

    # The expected wheels were produced.
    ios_version = os.getenv("IPHONEOS_DEPLOYMENT_TARGET", "13.0").replace(".", "_")
    platform_machine = platform.machine()

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

    # The warnings about cross-build notifications were silenced.
    captured = capfd.readouterr()
    assert "Your project configuration does not define any cross-build tools." not in captured.err
