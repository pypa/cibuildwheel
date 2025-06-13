from __future__ import annotations

import os
import platform
import shutil
import subprocess
import textwrap

import pytest

from cibuildwheel.ci import CIProvider, detect_ci_provider

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


def skip_if_ios_testing_not_supported() -> None:
    """Skip the test if iOS testing is not supported on this machine."""
    if utils.get_platform() != "macos":
        pytest.skip("this test can only run on macOS")
    if utils.get_xcode_version() < (13, 0):
        pytest.skip("this test only works with Xcode 13.0 or greater")
    if detect_ci_provider() == CIProvider.cirrus_ci:
        pytest.skip(
            "iOS testing not currently supported on Cirrus CI due to a failure "
            "to start the simulator."
        )


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
    skip_if_ios_testing_not_supported()

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
            "CIBW_TEST_COMMAND": "python -m this && python -m unittest discover tests test_platform.py",
            "CIBW_BUILD_VERBOSITY": "1",
            **build_config,
        },
    )

    # The expected wheels were produced.
    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", platform="ios", python_abi_tags=["cp313-cp313"]
    )
    assert set(actual_wheels) == set(expected_wheels)

    # The user was notified that the cross-build tool was found.
    captured = capfd.readouterr()
    assert "'does-exist' will be included in the cross-build environment" in captured.out

    # Make sure the first command ran
    assert "Zen of Python" in captured.out


@pytest.mark.serial
def test_no_test_sources(tmp_path, capfd):
    """Build will provide a helpful error if pytest is run and test-sources is not defined."""
    skip_if_ios_testing_not_supported()

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
                "CIBW_TEST_REQUIRES": "pytest",
                "CIBW_TEST_COMMAND": "python -m pytest",
                "CIBW_XBUILD_TOOLS": "",
            },
        )

    # The error message indicates the configuration issue.
    captured = capfd.readouterr()
    assert (
        "you must copy your test files to the testbed app by setting the `test-sources` option"
        in captured.out + captured.err
    )


def test_ios_testing_with_placeholder(tmp_path, capfd):
    """
    Tests with the {project} placeholder are not supported on iOS, because the test command
    is run in the simulator.
    """
    skip_if_ios_testing_not_supported()

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
                "CIBW_TEST_REQUIRES": "pytest",
                "CIBW_TEST_COMMAND": "pytest {project}/tests",
                "CIBW_XBUILD_TOOLS": "",
            },
        )

    # The error message indicates the configuration issue.
    captured = capfd.readouterr()
    assert "iOS tests cannot use placeholders" in captured.out + captured.err


@pytest.mark.serial
def test_ios_test_command_short_circuit(tmp_path, capfd):
    skip_if_ios_testing_not_supported()

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files.update(basic_project_files)
    basic_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        # `python -m not_a_module` will fail, so `python -m this` should not be run.
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_PLATFORM": "ios",
                "CIBW_BUILD": "cp313-*",
                "CIBW_XBUILD_TOOLS": "",
                "CIBW_TEST_SOURCES": "tests",
                "CIBW_TEST_COMMAND": "python -m not_a_module && python -m this",
                "CIBW_BUILD_VERBOSITY": "1",
            },
        )

    captured = capfd.readouterr()

    assert "No module named not_a_module" in captured.out + captured.err
    # assert that `python -m this` was not run
    assert "Zen of Python" not in captured.out + captured.err


def test_missing_xbuild_tool(tmp_path, capfd):
    """Build will fail if xbuild-tools references a non-existent tool."""
    skip_if_ios_testing_not_supported()

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
                "CIBW_TEST_COMMAND": "python -m tests",
                "CIBW_XBUILD_TOOLS": "does-not-exist",
            },
        )

    # The error message indicates the problem tool.
    captured = capfd.readouterr()
    assert "Could not find a 'does-not-exist' executable on the path." in captured.err


def test_no_xbuild_tool_definition(tmp_path, capfd):
    """Build will succeed with a warning if there is no xbuild-tools definition."""
    skip_if_ios_testing_not_supported()

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
    expected_wheels = utils.expected_wheels(
        "spam",
        "0.1.0",
        platform="ios",
        python_abi_tags=["cp313-cp313"],
    )
    assert set(actual_wheels) == set(expected_wheels)

    # The user was notified that there was no cross-build tool definition.
    captured = capfd.readouterr()
    assert "Your project configuration does not define any cross-build tools." in captured.err


def test_empty_xbuild_tool_definition(tmp_path, capfd):
    """Build will succeed with no warning if there is an empty xbuild-tools definition."""
    skip_if_ios_testing_not_supported()

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

    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", platform="ios", python_abi_tags=["cp313-cp313"]
    )
    assert set(actual_wheels) == set(expected_wheels)

    # The warnings about cross-build notifications were silenced.
    captured = capfd.readouterr()
    assert "Your project configuration does not define any cross-build tools." not in captured.err


@pytest.mark.serial
def test_ios_test_command_without_python_dash_m(tmp_path, capfd):
    """pytest should be able to run without python -m, but it should warn."""
    skip_if_ios_testing_not_supported()

    project_dir = tmp_path / "project"

    project = test_projects.new_c_project()
    project.files["tests/__init__.py"] = ""
    project.files["tests/test_spam.py"] = textwrap.dedent("""
        import spam
        def test_spam():
            assert spam.filter("spam") == 0
            assert spam.filter("ham") != 0
    """)
    project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_PLATFORM": "ios",
            "CIBW_BUILD": "cp313-*",
            "CIBW_TEST_COMMAND": "pytest ./tests",
            "CIBW_TEST_SOURCES": "tests",
            "CIBW_TEST_REQUIRES": "pytest",
            "CIBW_XBUILD_TOOLS": "",
        },
    )

    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", platform="ios", python_abi_tags=["cp313-cp313"]
    )
    assert set(actual_wheels) == set(expected_wheels)

    out, err = capfd.readouterr()

    assert "iOS tests configured with a test command which doesn't start with 'python -m'" in err


def test_ios_test_command_invalid(tmp_path, capfd):
    """Test command should raise an error if it's clearly invalid."""
    skip_if_ios_testing_not_supported()

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.files["./my_test_script.sh"] = "echo hello"
    basic_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_PLATFORM": "ios",
                "CIBW_TEST_COMMAND": "./my_test_script.sh",
                "CIBW_TEST_SOURCES": "./my_test_script.sh",
                "CIBW_XBUILD_TOOLS": "",
            },
        )
    out, err = capfd.readouterr()
    assert "iOS tests configured with a test command which doesn't start with 'python -m'" in err
