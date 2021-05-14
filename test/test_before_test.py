from . import test_projects, utils

before_test_project = test_projects.new_c_project()
before_test_project.files[
    "test/spam_test.py"
] = r"""
import sys
import os
from unittest import TestCase


class TestBeforeTest(TestCase):
    def test_version(self):
        # assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_TEST step
        # is the same one as is currently running.
        # because of use symlinks in MacOS run this test is also need
        version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
        with open(version_file) as f:
            stored_version = f.read()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

    def test_prefix(self):
        # check that the prefix also was written
        prefix_file = 'c:\\pythonprefix.txt' if sys.platform == 'win32' else '/tmp/pythonprefix.txt'
        with open(prefix_file) as f:
            stored_prefix = f.read()
        print('stored_prefix', stored_prefix)
        print('sys.prefix', sys.prefix)
        #  Works around path-comparison bugs caused by short-paths on Windows e.g.
        #  vssadm~1 instead of vssadministrator

        assert os.stat(stored_prefix) == os.stat(sys.prefix)
"""


def test(tmp_path):
    project_dir = tmp_path / "project"
    before_test_project.generate(project_dir)
    test_project_dir = project_dir / "dependency"
    test_projects.new_c_project().generate(test_project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # write python version information to a temporary file, this is
            # checked in setup.py
            "CIBW_BEFORE_TEST": """python -c "import sys; open('/tmp/pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('/tmp/pythonprefix.txt', 'w').write(sys.prefix)" && python -m pip install {project}/dependency""",
            "CIBW_BEFORE_TEST_WINDOWS": """python -c "import sys; open('c:\\pythonversion.txt', 'w').write(sys.version)" && python -c "import sys; open('c:\\pythonprefix.txt', 'w').write(sys.prefix)" && python -m pip install {project}/dependency""",
            "CIBW_TEST_REQUIRES": "pytest",
            # the 'false ||' bit is to ensure this command runs in a shell on
            # mac/linux.
            "CIBW_TEST_COMMAND": "false || pytest {project}/test",
            "CIBW_TEST_COMMAND_WINDOWS": "pytest {project}/test",
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
