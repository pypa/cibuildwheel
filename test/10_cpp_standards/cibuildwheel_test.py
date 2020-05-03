import os

import pytest

import utils

project_dir = os.path.dirname(__file__)


def test_cpp11(tmp_path):
    # This test checks that the C++11 standard is supported

    # VC++ for Python 2.7 does not support modern standards
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32', 'CIBW_ENVIRONMENT': 'STANDARD=11'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w and 'pp27-pypy_73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp14():
    # This test checks that the C++14 standard is supported

    # VC++ for Python 2.7 does not support modern standards
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.4 and 3.5 are compiled with MSVC 10, which does not support C++14
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32 cp35-win*', 'CIBW_ENVIRONMENT': 'STANDARD=14'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w
                       and 'cp35-cp35m-win' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp17():
    # This test checks that the C++17 standard is supported

    # Python and PyPy 2.7 use the `register` keyword which is forbidden in the C++17 standard
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.5 and PyPy 3.6 are compiled with MSVC 10, which does not support C++17
    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32 cp35-win* pp36-win32', 'CIBW_ENVIRONMENT': 'STANDARD=17'}

    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.13'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', macosx_deployment_target='10.13')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w
                       and 'cp35-cp35m-win' not in w
                       and 'pp36-pypy36_pp73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp17_modern_msvc_workaround(tmp_path):
    # This test checks the workaround for modern C++ versions, using a modern compiler

    if utils.platform != 'windows':
        pytest.skip('the test is only relevant to the Windows build')

    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    # VC++ for Python 2.7 and MSVC 10 do not support modern standards
    # This is a workaround which forces distutils/setupstools to a newer version
    # Wheels compiled need a more modern C++ redistributable installed, which is not
    # included with Python: see documentation for more info
    # DISTUTILS_USE_SDK and MSSdk=1 tell distutils/setuptools that we are adding
    # MSVC's compiler, tools, and libraries to PATH ourselves
    add_env = {'CIBW_ENVIRONMENT': 'STANDARD=17',
               'DISTUTILS_USE_SDK': '1', 'MSSdk': '1'}

    # Use existing setuptools code to run Visual Studio's vcvarsall.bat and get the
    # necessary environment variables, since running vcvarsall.bat in a subprocess
    # does not keep the relevant environment variables
    # In normal CI setup: run vcvarsall.bat before running cibuildwheel
    import setuptools

    # Different environment variables for 32-bit/64-bit targets
    # First, 32-bit (or x86)
    vcvarsall_env = setuptools.msvc.msvc14_get_vc_env('x86')
    add_env_x86 = add_env.copy()
    add_env_x86['CIBW_BUILD'] = '*-win32'
    for vc_var in ['path', 'include', 'lib']:
        add_env_x86[vc_var] = vcvarsall_env[vc_var]
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env_x86)

    # Then, 64-bit (or x64)
    vcvarsall_env = setuptools.msvc.msvc14_get_vc_env('x64')
    add_env_x64 = add_env.copy()
    add_env_x64['CIBW_BUILD'] = '*-win_amd64'
    for vc_var in ['path', 'include', 'lib']:
        add_env_x64[vc_var] = vcvarsall_env[vc_var]
    actual_wheels += utils.cibuildwheel_run(project_dir, add_env=add_env_x64)

    expected_wheels = utils.expected_wheels('spam', '0.1.0')

    assert set(actual_wheels) == set(expected_wheels)
