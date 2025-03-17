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


# iOS tests shouldn't be run in parallel, because they're dependent on starting
# a simulator. It's *possible* to start multiple simulators, but not advisable
# to start as many simulators as there are CPUs on the test machine.
@pytest.mark.xdist_group(name="ios")
@pytest.mark.parametrize(
    "build_config",
    [
        # Default to the pip build frontend
        {"CIBW_PLATFORM": "ios"},
        # Also check the build frontend
        {"CIBW_PLATFORM": "ios", "CIBW_BUILD_FRONTEND": "build"},
    ],
)
def test_ios_platforms(tmp_path, build_config, monkeypatch):
    if utils.platform != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")
    if "CIBW_SAFE_TOOLS" in build_config and shutil.which("cmake") is None:
        pytest.xfail("test machine doesn't have cmake installed")

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

    # Build the wheels. Mark the "does-exist" tool as safe, and invoke it during
    # a `before-build` step. It will also be invoked when `setup.py` is invoked.
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BEFORE_BUILD": "does-exist",
            "CIBW_BUILD": "cp313-*",
            "CIBW_SAFE_TOOLS": "does-exist",
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


def test_no_test_sources(tmp_path, capfd):
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

    captured = capfd.readouterr()
    assert "Testing on iOS requires a definition of test-sources." in captured.err


def test_missing_safe_tool(tmp_path, capfd):
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
                "CIBW_SAFE_TOOLS": "does-not-exist",
            },
        )

    captured = capfd.readouterr()
    assert "Could not find a 'does-not-exist' executable on the path." in captured.err
