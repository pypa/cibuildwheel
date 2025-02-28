from pathlib import Path

import jinja2

from . import utils
from .test_projects import TestProject
from .test_projects.c import SPAM_C_TEMPLATE

subdir_package_project = TestProject()

subdir_package_project.files["src/spam/spam.c"] = jinja2.Template(SPAM_C_TEMPLATE)
subdir_package_project.template_context["spam_c_top_level_add"] = ""
subdir_package_project.template_context["spam_c_function_add"] = ""

subdir_package_project.files["src/spam/setup.py"] = r"""
from setuptools import Extension, setup

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
"""

subdir_package_project.files["src/spam/test/run_tests.py"] = r"""
print('run_tests.py executed!')
"""

subdir_package_project.files["bin/before_build.py"] = r"""
print('before_build.py executed!')
"""


def test(capfd, tmp_path):
    project_dir = tmp_path / "project"
    subdir_package_project.generate(project_dir)

    package_dir = Path("src", "spam")
    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        package_dir=package_dir,
        add_env={
            "CIBW_BEFORE_BUILD": "python {project}/bin/before_build.py",
            "CIBW_TEST_COMMAND": "python {package}/test/run_tests.py",
        },
        single_python=True,
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)

    captured = capfd.readouterr()
    assert "before_build.py executed!" in captured.out
    assert "run_tests.py executed!" in captured.out
