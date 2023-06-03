from __future__ import annotations

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


def test_podman(tmp_path, capfd, request):
    if utils.platform != "linux":
        pytest.skip("the test is only relevant to the linux build")

    if not request.config.getoption("--run-podman"):
        pytest.skip("needs --run-podman option to run")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build some musllinux and manylinux wheels (ensuring that we use two containers)
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp310-*{manylinux,musllinux}_x86_64",
            "CIBW_BEFORE_ALL": "echo 'test log statement from before-all'",
            "CIBW_CONTAINER_ENGINE": "podman",
        },
    )

    # check that the expected wheels are produced
    expected_wheels = [
        w
        for w in utils.expected_wheels("spam", "0.1.0")
        if ("-cp310-" in w) and ("x86_64" in w) and ("manylinux" in w or "musllinux" in w)
    ]
    assert set(actual_wheels) == set(expected_wheels)

    # check that stdout is bring passed-though from container correctly
    captured = capfd.readouterr()
    assert "test log statement from before-all" in captured.out


def test_create_args(tmp_path, capfd):
    if utils.platform != "linux":
        pytest.skip("the test is only relevant to the linux build")

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build a manylinux wheel, using create_args to set an environment variable
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp310-manylinux_*",
            "CIBW_BEFORE_ALL": "echo TEST_CREATE_ARGS is set to $TEST_CREATE_ARGS",
            "CIBW_CONTAINER_ENGINE": "docker; create_args: --env=TEST_CREATE_ARGS=itworks",
        },
    )

    expected_wheels = [
        w for w in utils.expected_wheels("spam", "0.1.0") if ("cp310-manylinux" in w)
    ]
    assert set(actual_wheels) == set(expected_wheels)

    captured = capfd.readouterr()
    assert "TEST_CREATE_ARGS is set to itworks" in captured.out
