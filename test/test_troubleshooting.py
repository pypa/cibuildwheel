import subprocess

import pytest

from . import utils
from .test_projects import TestProject, new_c_project

SO_FILE_WARNING = "NOTE: Shared object (.so) files found in this project."


@pytest.mark.parametrize("project_contains_so_files", [False, True])
def test_failed_build_with_so_files(tmp_path, capfd, build_frontend_env, project_contains_so_files):
    project = TestProject()
    project.files["setup.py"] = "raise Exception('this build will fail')\n"
    if project_contains_so_files:
        project.files["libnothing.so"] = ""

    if utils.get_platform() != "linux":
        pytest.skip("this test is only relevant to the linux build")

    project_dir = tmp_path / "project"
    project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, add_env=build_frontend_env)

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)

    if project_contains_so_files:
        assert SO_FILE_WARNING in captured.err
    else:
        assert SO_FILE_WARNING not in captured.err


@pytest.mark.parametrize("project_contains_so_files", [False, True])
def test_failed_repair_with_so_files(tmp_path, capfd, project_contains_so_files):
    if utils.get_platform() != "linux":
        pytest.skip("this test is only relevant to the linux build")

    project = new_c_project()

    if project_contains_so_files:
        project.files["libnothing.so"] = ""

    project_dir = tmp_path / "project"
    project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, add_env={"CIBW_REPAIR_WHEEL_COMMAND": "false"})

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)

    if project_contains_so_files:
        assert SO_FILE_WARNING in captured.err
    else:
        assert SO_FILE_WARNING not in captured.err
