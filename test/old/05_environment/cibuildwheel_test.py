import os
import pytest
import subprocess
import utils


def test():
    project_dir = os.path.dirname(__file__)

    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup.py
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ENVIRONMENT': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH=$PATH:/opt/cibw_test_path''',
        'CIBW_ENVIRONMENT_WINDOWS': '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH="$PATH;/opt/cibw_test_path"''',
    })

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)


def test_overridden_path(tmp_path):
    project_dir = os.path.dirname(__file__)

    # mess up PATH, somehow
    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, output_dir=tmp_path, add_env={
            'CIBW_ENVIRONMENT': '''SOMETHING="$(mkdir new_path && touch new_path/python)" PATH="$(realpath new_path):$PATH"''',
            'CIBW_ENVIRONMENT_WINDOWS': '''SOMETHING="$(mkdir new_path && type nul > new_path/python.exe)" PATH="$CD\\new_path;$PATH"''',
        })
    assert len(os.listdir(str(tmp_path))) == 0
