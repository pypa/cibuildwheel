import os
from utils import utils


PROJECT_DIR = os.path.dirname(__file__)


def test(utils):
    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup.py
    utils.cibuildwheel_run(PROJECT_DIR, add_env={
        'CIBW_ENVIRONMENT': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH=$PATH:/opt/cibw_test_path''',
        'CIBW_ENVIRONMENT_WINDOWS': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH="$PATH;/opt/cibw_test_path"''',
    })

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = utils.list_wheels()
    assert set(actual_wheels) == set(expected_wheels)
