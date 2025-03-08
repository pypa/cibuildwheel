import subprocess

import pytest

from test import test_projects

from . import utils

pure_python_project = test_projects.TestProject()
pure_python_project.files["setup.py"] = """
from setuptools import Extension, setup

setup(
    name="spam",
    py_modules=['spam'],
    version="0.1.0",
)
"""

pure_python_project.files["spam.py"] = """
def a_function():
    pass
"""


def test(tmp_path, capfd):
    # this test checks that if a pure wheel is generated, the build should
    # fail.
    project_dir = tmp_path / "project"
    pure_python_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        print("produced wheels:", utils.cibuildwheel_run(project_dir))

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)
    assert exc_info.value.returncode == 5
    assert "Build failed because a pure Python wheel was generated" in captured.err
