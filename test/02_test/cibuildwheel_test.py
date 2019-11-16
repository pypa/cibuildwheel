import os, subprocess
import pytest
from utils import utils


PROJECT_DIR = os.path.dirname(__file__)


def test(utils):
    # build and test the wheels
    utils.cibuildwheel_run(PROJECT_DIR, add_env={
        'CIBW_TEST_REQUIRES': 'nose',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = utils.list_wheels()
    assert set(actual_wheels) == set(expected_wheels)


def test_extras_require(utils):
    # build and test the wheels
    utils.cibuildwheel_run(PROJECT_DIR, add_env={
        'CIBW_TEST_EXTRAS': 'test',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'nosetests {project}/test',
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = utils.list_wheels()
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_test(utils):
    '''Ensure a failing test causes cibuildwheel to error out and exit'''
    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(PROJECT_DIR, add_env={
            'CIBW_TEST_COMMAND': 'false',
            # manylinux1 has a version of bash that's been shown to have
            # problems with this, so let's check that.
            'CIBW_MANYLINUX_I686_IMAGE': 'manylinux1',
            'CIBW_MANYLINUX_X86_64_IMAGE': 'manylinux1',
        })

    assert len(utils.list_wheels()) == 0

