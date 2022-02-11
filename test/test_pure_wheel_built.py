from test import test_projects

from . import utils

pure_python_project = test_projects.TestProject()
pure_python_project.files[
    "setup.py"
] = """
from setuptools import Extension, setup

setup(
    name="spam",
    py_modules=['spam'],
    version="0.1.0",
)
"""

pure_python_project.files[
    "spam.py"
] = """
def a_function():
    pass
"""


def test(tmp_path, capfd):
    # this test checks that if a pure wheel is generated, the build should
    # pass with the pure wheel option.
    project_dir = tmp_path / "project"
    pure_python_project.generate(project_dir)

    env = {
        "CIBW_PURE_WHEEL": "yes",
        # this shouldn't depend on the version of python, so build only CPython 3.6
        "CIBW_BUILD": "cp36-*",
    }

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=env)
    print("produced wheels:", actual_wheels)

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)
    assert "Build failed because a pure Python wheel was generated" not in captured.err

    # check that the expected wheels are produced
    expected_wheels = ["spam-0.1.0-py3-none-any.whl"]
    assert set(actual_wheels) == set(expected_wheels)
