import os
import subprocess

import pytest

import utils


def test():
    project_dir = os.path.dirname(__file__)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_TEST_REQUIRES': 'nose',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)


def test_extras_require():
    project_dir = os.path.dirname(__file__)

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_TEST_EXTRAS': 'test',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_test(tmp_path):
    '''Ensure a failing test causes cibuildwheel to error out and exit'''
    project_dir = os.path.dirname(__file__)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, output_dir=tmp_path, add_env={
            'CIBW_TEST_COMMAND': 'false',
            # manylinux1 has a version of bash that's been shown to have
            # problems with this, so let's check that.
            'CIBW_MANYLINUX_I686_IMAGE': 'manylinux1',
            'CIBW_MANYLINUX_X86_64_IMAGE': 'manylinux1',
        })
    assert len(os.listdir(str(tmp_path))) == 0
