import os
import platform

import pytest

import utils

project_dir = os.path.dirname(__file__)


@pytest.mark.parametrize("build_prefix", ["cp27", "cp35", "cp36", "cp37", "cp38", "pp27", "pp36"])
def test_single(build_prefix):
    """To force installation all python for test"""
    project_dir = os.path.dirname(__file__)
    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': build_prefix + "*",
    })
    expected_wheels = [x for x in utils.expected_wheels('spam', '0.1.0') if build_prefix in x]
    assert set(actual_wheels) == set(expected_wheels)


def test():
    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)


def test_build_identifiers():
    # check that the number of expected wheels matches the number of build
    # identifiers
    # after adding CIBW_MANYLINUX_IMAGE to support manylinux2010, there
    # can be multiple wheels for each wheel, though, so we need to limit
    # the expected wheels
    if platform.machine() in ['x86_64', 'i686']:
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-manylinux' not in w or '-manylinux1' in w]
    else:
        expected_wheels = utils.expected_wheels('spam', '0.1.0')
    build_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    assert len(expected_wheels) == len(build_identifiers)
