from . import test_projects, utils

before_test_project = test_projects.new_c_project()
before_test_project.files["test/spam_test.py"] = r"""
import sys
import os
from pathlib import Path
from unittest import TestCase

PROJECT_DIR = Path(__file__).parent.parent.resolve()


class TestBeforeTest(TestCase):
    def test_version(self):
        # assert that the Python version as written to pythonversion_bt.txt in the CIBW_BEFORE_TEST step
        # is the same one as is currently running.
        # because of use symlinks in MacOS run this test is also need
        stored_version = PROJECT_DIR.joinpath('pythonversion_bt.txt').read_text()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

    def test_prefix(self):
        # check that the prefix also was written
        stored_prefix = PROJECT_DIR.joinpath('pythonprefix_bt.txt').read_text()
        print('stored_prefix', stored_prefix)
        print('sys.prefix', sys.prefix)
        #  Works around path-comparison bugs caused by short-paths on Windows e.g.
        #  vssadm~1 instead of vssadministrator

        assert os.path.samefile(stored_prefix, sys.prefix)
"""


def test(tmp_path, build_frontend_env):
    project_dir = tmp_path / "project"
    before_test_project.generate(project_dir)
    test_project_dir = project_dir / "dependency"
    test_projects.new_c_project().generate(test_project_dir)

    before_test_steps = [
        '''python -c "import pathlib, sys; pathlib.Path('{project}/pythonversion_bt.txt').write_text(sys.version)"''',
        '''python -c "import pathlib, sys; pathlib.Path('{project}/pythonprefix_bt.txt').write_text(sys.prefix)"''',
    ]

    if utils.get_platform() == "pyodide":
        before_test_steps.extend(
            ["pyodide build {project}/dependency", "pip install --find-links dist/ spam"]
        )
    elif build_frontend_env["CIBW_BUILD_FRONTEND"] in {"pip", "build"}:
        before_test_steps.append("python -m pip install {project}/dependency")

    before_test = " && ".join(before_test_steps)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # write python version information to a temporary file, this is
            # checked in setup.py
            "CIBW_BEFORE_TEST": before_test,
            "CIBW_TEST_REQUIRES": "pytest",
            # the 'false ||' bit is to ensure this command runs in a shell on
            # mac/linux.
            "CIBW_TEST_COMMAND": f"false || {utils.invoke_pytest()} {{project}}/test",
            # pytest fails on GraalPy 24.2.0 on Windows so we skip it there
            # until https://github.com/oracle/graalpython/issues/490 is fixed
            "CIBW_TEST_COMMAND_WINDOWS": "where graalpy || pytest {project}/test",
            **build_frontend_env,
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
