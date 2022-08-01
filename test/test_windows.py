from __future__ import annotations

import textwrap

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


@pytest.mark.parametrize("use_pyproject_toml", [True, False])
def test_wheel_tag_is_correct_when_using_windows_cross_compile(tmp_path, use_pyproject_toml):
    if utils.platform != "windows":
        pytest.skip("This test is only relevant to Windows")

    if use_pyproject_toml:
        basic_project.files["pyproject.toml"] = textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools"]
            build-backend = "setuptools.build_meta"
            """
        )

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp310-*",
        },
        add_args=["--platform", "windows", "--archs", "ARM64"],
    )

    # check that the expected wheels are produced
    expected_wheels = [
        "spam-0.1.0-cp310-win_arm64.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
