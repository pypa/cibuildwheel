import itertools
import subprocess

import pytest

from . import test_projects, utils

project_with_a_test = test_projects.new_c_project()

project_with_a_test.files["test/spam_test.py"] = r"""
import spam

def test_spam():
    assert spam.filter("spam") == 0
    assert spam.filter("ham") != 0
"""


def test(tmp_path, request):
    archs = request.config.getoption("--run-emulation")
    if archs is None:
        pytest.skip("needs --run-emulation option to run")

    if archs == "all":
        archs = " ".join(utils.EMULATED_ARCHS)

    project_dir = tmp_path / "project"
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "pytest",
            "CIBW_TEST_COMMAND": "pytest {project}/test",
            "CIBW_ARCHS": archs,
            # TODO remove me once proper support is added
            "CIBW_MANYLINUX_RISCV64_IMAGE": "ghcr.io/mayeut/manylinux_2_35:2025.05.11-1",
            "CIBW_SKIP": "*-musllinux_riscv64",
        },
    )

    # also check that we got the right wheels
    expected_wheels = list(
        itertools.chain.from_iterable(
            utils.expected_wheels("spam", "0.1.0", machine_arch=arch, single_arch=True)
            for arch in archs.split(" ")
        )
    )
    # TODO remove me once proper support is added
    expected_wheels = [wheel for wheel in expected_wheels if "musllinux_1_2_riscv64" not in wheel]
    assert set(actual_wheels) == set(expected_wheels)


def test_setting_arch_on_other_platforms(tmp_path, capfd):
    if utils.get_platform() == "linux":
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
