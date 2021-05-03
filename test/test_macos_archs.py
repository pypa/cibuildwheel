import platform
import subprocess
from typing import Tuple

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()

ALL_MACOS_WHEELS = {
    *utils.expected_wheels("spam", "0.1.0", machine_arch="x86_64"),
    *utils.expected_wheels("spam", "0.1.0", machine_arch="arm64"),
}


def get_xcode_version() -> Tuple[int, int]:
    output = subprocess.run(
        ["xcodebuild", "-version"],
        universal_newlines=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    lines = output.splitlines()
    _, version_str = lines[0].split()

    version_parts = version_str.split(".")
    return (int(version_parts[0]), int(version_parts[1]))


def test_cross_compiled_build(tmp_path):
    if utils.platform != "macos":
        pytest.skip("this test is only relevant to macos")
    if get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp39-*",
            "CIBW_ARCHS": "x86_64, universal2, arm64",
        },
    )

    expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp39" in w]
    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.parametrize("build_universal2", [False, True])
def test_cross_compiled_test(tmp_path, capfd, build_universal2):
    if utils.platform != "macos":
        pytest.skip("this test is only relevant to macos")
    if get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp39-*",
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
            "CIBW_ARCHS": "universal2" if build_universal2 else "x86_64 arm64",
        },
    )

    captured = capfd.readouterr()

    if platform.machine() == "x86_64":
        # ensure that tests were run on only x86_64
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" not in captured.out
        if build_universal2:
            assert (
                "While universal2 wheels can be built on x86_64, the arm64 part of them cannot currently be tested"
                in captured.err
            )
        else:
            assert (
                "While arm64 wheels can be built on x86_64, they cannot be tested" in captured.err
            )
    elif platform.machine() == "arm64":
        # ensure that tests were run on both x86_64 and arm64
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" in captured.out

    if build_universal2:
        expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp39" in w and "universal2" in w]
    else:
        expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp39" in w and "universal2" not in w]

    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.parametrize("skip_arm64_test", [False, True])
def test_universal2_testing(tmp_path, capfd, skip_arm64_test):
    if utils.platform != "macos":
        pytest.skip("this test is only relevant to macos")
    if get_xcode_version() < (12, 2):
        pytest.skip("this test only works with Xcode 12.2 or greater")
    if platform.machine() != "x86_64":
        pytest.skip("this test only works on x86_64")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp39-*",
            "CIBW_TEST_COMMAND": '''python -c "import platform; print('running tests on ' + platform.machine())"''',
            "CIBW_ARCHS": "universal2",
            "CIBW_TEST_SKIP": "*_universal2:arm64" if skip_arm64_test else "",
        },
    )

    captured = capfd.readouterr()

    if platform.machine() == "x86_64":
        assert "running tests on x86_64" in captured.out
        assert "running tests on arm64" not in captured.out

        warning_message = "While universal2 wheels can be built on x86_64, the arm64 part of them cannot currently be tested"
        if skip_arm64_test:
            assert warning_message not in captured.err
        else:
            assert warning_message in captured.err

    expected_wheels = [w for w in ALL_MACOS_WHEELS if "cp39" in w and "universal2" in w]

    assert set(actual_wheels) == set(expected_wheels)
