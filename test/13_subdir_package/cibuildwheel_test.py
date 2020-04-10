import os
import utils

project_dir = os.path.dirname(__file__)


def test():
    package_dir = os.path.join(project_dir, 'src', 'spam')
    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, package_dir=package_dir, add_env={
        'CIBW_BEFORE_BUILD': '{project}/bin/before_build.sh',
        'CIBW_TEST_COMMAND': 'python {package}/test/run_tests.py',
        # this shouldn't depend on the version of python, so build only
        # CPython 3.6
        'CIBW_BUILD': 'cp36-*',
    })

    # check that the expected wheels are produced
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp36' in w]
    assert set(actual_wheels) == set(expected_wheels)
