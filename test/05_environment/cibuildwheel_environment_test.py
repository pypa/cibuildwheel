import os

from shared import utils


def test(tmp_path):
    project_dir = os.path.dirname(__file__)

    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup.py
    utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ENVIRONMENT': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH=$PATH:/opt/cibw_test_path''',
        'CIBW_ENVIRONMENT_WINDOWS': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH="$PATH;/opt/cibw_test_path"''',
    }, output_dir=tmp_path)

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = [x.name for x in tmp_path.iterdir()]
    assert set(actual_wheels) == set(expected_wheels)
