import os
import utils

def test():
    project_dir = os.path.dirname(__file__)

    # build and test the wheels
    utils.run_cibuildwheel(project_dir, add_env={
        'CIBW_TEST_REQUIRES': 'nose',
        # the 'false ||' bit is to ensure this command runs in a shell on
        # mac/linux.
        'CIBW_TEST_COMMAND': 'false || nosetests {project}/test',
        'CIBW_TEST_COMMAND_WINDOWS': 'nosetests {project}/test',
    })
    
    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = os.listdir('wheelhouse')
    assert set(actual_wheels) == set(expected_wheels)
