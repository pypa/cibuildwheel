import subprocess

import pytest

from . import utils
from .test_projects import TestProject

so_file_project = TestProject()

so_file_project.files["libnothing.so"] = ""

so_file_project.files[
    "setup.py"
] = """
raise Exception('this build will fail')
"""


def test_failed_project_with_so_files(tmp_path, capfd, build_frontend_env):
    if utils.platform != "linux":
        pytest.skip("this test is only relevant to the linux build")

    project_dir = tmp_path / "project"
    so_file_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, add_env=build_frontend_env)

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)
    assert "NOTE: Shared object (.so) files found in this project." in captured.err
