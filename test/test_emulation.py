import subprocess

import pytest

from . import test_projects, utils

project_with_a_test = test_projects.new_c_project()

project_with_a_test.files[
    "test/spam_test.py"
] = r"""
import spam

def test_spam():
    assert spam.system('python -c "exit(0)"') == 0
    assert spam.system('python -c "exit(1)"') != 0
"""


@pytest.mark.emulation
def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "pytest",
            "CIBW_TEST_COMMAND": "pytest {project}/test",
            "CIBW_ARCHS": "aarch64 ppc64le s390x",
        },
    )

    # also check that we got the right wheels
    expected_wheels = (
        utils.expected_wheels("spam", "0.1.0", machine_arch="aarch64")
        + utils.expected_wheels("spam", "0.1.0", machine_arch="ppc64le")
        + utils.expected_wheels("spam", "0.1.0", machine_arch="s390x")
    )
    assert set(actual_wheels) == set(expected_wheels)


def test_setting_arch_on_other_platforms(tmp_path, capfd):
    if utils.platform == "linux":
        pytest.skip("this test checks the behaviour on platforms other than linux")

    project_dir = tmp_path / "project"
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_ARCHS": "aarch64",
            },
        )

    captured = capfd.readouterr()
    assert "Invalid archs option" in captured.err
