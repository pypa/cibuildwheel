import os
import subprocess
import textwrap

import pytest

from . import test_projects, utils

project_with_a_test = test_projects.new_c_project(
    setup_cfg_add=textwrap.dedent(
        r"""
        [options.extras_require]
        test = pytest
        """
    )
)

project_with_a_test.files[
    "test/spam_test.py"
] = r'''
import os
import platform
import sys
import struct
from unittest import TestCase

import spam


def path_contains(parent, child):
    """ returns True if `child` is inside `parent`.
    Works around path-comparison bugs caused by short-paths on Windows e.g.
    vssadm~1 instead of vssadministrator
    """
    parent = os.path.abspath(parent)
    child = os.path.abspath(child)

    while child != os.path.dirname(child):
        child = os.path.dirname(child)
        if os.stat(parent) == os.stat(child):
            # parent and child refer to the same directory on the filesystem
            return True
    return False


class TestSpam(TestCase):
    def test_system(self):
        self.assertEqual(0, spam.system('python -c "exit(0)"'))
        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))

    def test_virtualenv(self):
        # sys.prefix is different from sys.base_prefix when running a virtualenv
        # See https://docs.python.org/3/library/venv.html, which virtualenv seems
        # to honor in recent releases
        if sys.prefix == sys.base_prefix:
            self.fail("Not running in a virtualenv")

        self.assertTrue(path_contains(sys.prefix, sys.executable))
        self.assertTrue(path_contains(sys.prefix, spam.__file__))

    def test_uname(self):
        if platform.system() == "Windows":
            return
        # if we're running in 32-bit Python, check that the machine is i686.
        # See #336 for more info.
        bits = struct.calcsize("P") * 8
        if bits == 32:
            self.assertEqual(platform.machine(), "i686")
'''


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "pytest",
            # the 'false ||' bit is to ensure this command runs in a shell on
            # mac/linux.
            "CIBW_TEST_COMMAND": "false || pytest {project}/test",
            "CIBW_TEST_COMMAND_WINDOWS": "COLOR 00 || pytest {project}/test",
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)


def test_extras_require(tmp_path):
    project_dir = tmp_path / "project"
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_EXTRAS": "test",
            # the 'false ||' bit is to ensure this command runs in a shell on
            # mac/linux.
            "CIBW_TEST_COMMAND": "false || pytest {project}/test",
            "CIBW_TEST_COMMAND_WINDOWS": "COLOR 00 || pytest {project}/test",
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)


project_with_a_failing_test = test_projects.new_c_project()
project_with_a_failing_test.files[
    "test/spam_test.py"
] = r"""
from unittest import TestCase

class TestSpam(TestCase):
    def test_something(self):
        self.fail('this test is supposed to fail')
"""


def test_failing_test(tmp_path):
    """Ensure a failing test causes cibuildwheel to error out and exit"""
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"
    project_with_a_failing_test.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            output_dir=output_dir,
            add_env={
                "CIBW_TEST_REQUIRES": "nose",
                "CIBW_TEST_COMMAND": "nosetests {project}/test",
                # manylinux1 has a version of bash that's been shown to have
                # problems with this, so let's check that.
                "CIBW_MANYLINUX_I686_IMAGE": "manylinux1",
                "CIBW_MANYLINUX_X86_64_IMAGE": "manylinux1",
            },
        )

    assert len(os.listdir(output_dir)) == 0
