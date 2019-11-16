import os
from utils import utils


PROJECT_DIR = os.path.dirname(__file__)


def test(utils):
    # build the wheels
    utils.cibuildwheel_run(PROJECT_DIR)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = utils.list_wheels()
    assert set(actual_wheels) == set(expected_wheels)


def test_build_identifiers(utils):
    # check that the number of expected wheels matches the number of build
    # identifiers
    # after adding CIBW_MANYLINUX_IMAGE to support manylinux2010, there
    # can be multiple wheels for each wheel, though, so we need to limit
    # the expected wheels
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if not '-manylinux' in w or '-manylinux1' in w]
    build_identifiers = utils.cibuildwheel_get_build_identifiers(PROJECT_DIR)
    assert len(expected_wheels) == len(build_identifiers)
