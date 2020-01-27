import os, subprocess
import pytest, textwrap
from . import utils


def test(tmpdir):
    project_dir = str(tmpdir)

    # generate sample project with a test
    utils.generate_project(
        path=project_dir,
        extra_files=[
            ('test/spam_test.py', textwrap.dedent(u'''
                from unittest import TestCase
                import spam

                class TestSpam(TestCase):
                    def test_system(self):
                        self.assertEqual(0, spam.system('python -c "exit(0)"'))
                        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))
            '''))
        ],
    )
    
    # build and test the wheels
    utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_REQUIRES": "nose",
            # the 'false ||' bit is to ensure this command runs in a shell on
            # mac/linux.
            "CIBW_TEST_COMMAND": "false || nosetests {project}/test",
            "CIBW_TEST_COMMAND_WINDOWS": "nosetests {project}/test",
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    actual_wheels = os.listdir("wheelhouse")
    assert set(actual_wheels) == set(expected_wheels)


def test_extras_require(tmpdir):
    project_dir = str(tmpdir)

    utils.generate_project(
        path=project_dir,
        setup_py_setup_args_add='extras_require={"test": ["nose"]},',
        extra_files=[
            ('test/spam_test.py', textwrap.dedent(u'''
                from unittest import TestCase
                import spam

                class TestSpam(TestCase):
                    def test_system(self):
                        self.assertEqual(0, spam.system('python -c "exit(0)"'))
                        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))
            '''))
        ],
    )

    # build and test the wheels
    utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_TEST_EXTRAS": "test",
            "CIBW_TEST_COMMAND": "nosetests {project}/test",
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    actual_wheels = os.listdir("wheelhouse")
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_test():
    """Ensure a failing test causes cibuildwheel to error out and exit"""
    project_dir = os.path.dirname(__file__)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_TEST_COMMAND": "false",
                # manylinux1 has a version of bash that's been shown to have
                # problems with this, so let's check that.
                "CIBW_MANYLINUX_I686_IMAGE": "manylinux1",
                "CIBW_MANYLINUX_X86_64_IMAGE": "manylinux1",
            },
        )

    assert len(os.listdir("wheelhouse"))
