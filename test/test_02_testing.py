import os, subprocess
import pytest, textwrap
from . import utils
from .template_projects import CTemplateProject

project_with_a_test = CTemplateProject(
    setup_cfg_add=textwrap.dedent(r'''
        [options.extras_require]
        test = nose
    ''')
)

project_with_a_test.files['test/spam_test.py'] = r'''
from unittest import TestCase
import spam

class TestSpam(TestCase):
    def test_system(self):
        self.assertEqual(0, spam.system('python -c "exit(0)"'))
        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))
'''


def test(tmpdir):
    project_dir = str(tmpdir)
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_TEST_REQUIRES': 'nose',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'COLOR 00 || nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)



def test_extras_require(tmpdir):
    project_dir = str(tmpdir)
    project_with_a_test.generate(project_dir)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_TEST_EXTRAS': 'test',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'COLOR 00 || nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_test(tmp_path):
    """Ensure a failing test causes cibuildwheel to error out and exit"""
    project_dir = str(tmp_path / 'project')
    output_dir = str(tmp_path / 'output')
    project_with_a_test.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, output_dir=output_dir, add_env={
            'CIBW_TEST_COMMAND': 'false',
            # manylinux1 has a version of bash that's been shown to have
            # problems with this, so let's check that.
            'CIBW_MANYLINUX_I686_IMAGE': 'manylinux1',
            'CIBW_MANYLINUX_X86_64_IMAGE': 'manylinux1',
        })

    assert len(os.listdir(output_dir)) == 0

