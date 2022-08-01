from __future__ import annotations

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


def test_wheel_tag_is_correct_when_using_macosx_deployment_target(tmp_path):
    if utils.platform != "macos":
        pytest.skip("This test is only relevant to MACOSX_DEPLOYMENT_TARGET")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    deployment_target = "10.11"
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp39-*",
            "MACOSX_DEPLOYMENT_TARGET": deployment_target,
        },
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", macosx_deployment_target=deployment_target
    )
    expected_wheels = [w for w in expected_wheels if "cp39" in w]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
