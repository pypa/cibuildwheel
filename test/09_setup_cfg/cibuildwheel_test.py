import os
import utils


project_dir = os.path.dirname(__file__)

def test():
    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
