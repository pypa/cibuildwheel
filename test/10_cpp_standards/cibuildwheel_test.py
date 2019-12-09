import os
import sys 

import pytest

import utils


project_dir = os.path.dirname(__file__)

def test_cpp11(tmp_path):
    # This test checks that the C++11 standard is supported

    add_env = {'CIBW_SKIP': 'cp27-win*', 'CIBW_ENVIRONMENT': 'STANDARD=11'}
    # VC++ for Python 2.7 does not support modern standards
    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.9'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels(
                            'spam', '0.1.0', macosx_deployment_target='10.9')
                       if 'cp27-cp27m-win' not in x]
    assert set(actual_wheels) == set(expected_wheels)


def test_cpp14():
    # This test checks that the C++14 standard is supported

    add_env = {'CIBW_SKIP': 'cp27-win* cp35-win*', 'CIBW_ENVIRONMENT': 'STANDARD=14'}
    # VC++ for Python 2.7 does not support modern standards
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.4 and 3.5 are compiled with MSVC 10, which does not support C++14
    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.9'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels(
                            'spam', '0.1.0', macosx_deployment_target='10.9')
                       if 'cp27-cp27m-win' not in x and 'cp35-cp35m-win' not in x]
    assert set(actual_wheels) == set(expected_wheels)


def test_cpp17():
    # This test checks that the C++17 standard is supported

    # Python 2.7 uses the `register` keyword which is forbidden in the C++17 standard 
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.4 and 3.5 are compiled with MSVC 10, which does not support C++17
    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    add_env = {'CIBW_SKIP': 'cp27-win* cp35-win*', 'CIBW_ENVIRONMENT': 'STANDARD=17'}
    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.13'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [x for x in utils.expected_wheels(
                            'spam', '0.1.0', macosx_deployment_target='10.13')
                       if 'cp27-cp27m-win' not in x and 'cp35-cp35m-win' not in x]
    assert set(actual_wheels) == set(expected_wheels)
