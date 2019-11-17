'''
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
'''

import subprocess, sys, os, shutil
from tempfile import mkdtemp
from contextlib import contextmanager


IS_WINDOWS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')
IS_WINDOWS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'


# Python 2 does not have a tempfile.TemporaryDirectory context manager
@contextmanager
def TemporaryDirectoryIfNone(path):
    _path = path or mkdtemp()
    try:
        yield _path
    finally:
        if path is None:
            shutil.rmtree(_path)


def cibuildwheel_get_build_identifiers(project_path, env=None):
    '''
    Returns the list of build identifiers that cibuildwheel will try to build
    for the current platform.
    '''
    cmd_output = subprocess.check_output(
        [sys.executable, '-m', 'cibuildwheel', '--print-build-identifiers', project_path],
        universal_newlines=True,
        env=env,
    )

    return cmd_output.strip().split('\n')


def cibuildwheel_run(project_path, env=None, add_env=None, output_dir=None):
    '''
    Runs cibuildwheel as a subprocess, building the project at project_path.

    Uses the current Python interpreter.

    :param project_path: path of the project to be built.
    :param env: full environment to be used, os.environ if None
    :param add_env: environment used to update env
    :param output_dir: directory where wheels are saved. If None, a temporary
    directory will be used for the duration of the command.
    :return: list of built wheels (file names).
    '''
    if env is None:
        env = os.environ.copy()

    if add_env is not None:
        env.update(add_env)

    with TemporaryDirectoryIfNone(output_dir) as _output_dir:
        subprocess.check_call(
            [sys.executable, '-m', 'cibuildwheel', '--output-dir', str(_output_dir), project_path],
            env=env,
        )
        wheels = os.listdir(_output_dir)
    return wheels


def expected_wheels(package_name, package_version):
    '''
    Returns a list of expected wheels from a run of cibuildwheel.
    '''
    if platform == 'linux':
        templates = [
            '{package_name}-{package_version}-cp27-cp27m-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp27-cp27mu-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp35-cp35m-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp36-cp36m-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp37-cp37m-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp38-cp38-manylinux1_x86_64.whl',
            '{package_name}-{package_version}-cp27-cp27m-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp27-cp27mu-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp35-cp35m-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp36-cp36m-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp37-cp37m-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp38-cp38-manylinux2010_x86_64.whl',
            '{package_name}-{package_version}-cp27-cp27m-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp27-cp27mu-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp35-cp35m-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp36-cp36m-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp37-cp37m-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp38-cp38-manylinux1_i686.whl',
            '{package_name}-{package_version}-cp27-cp27m-manylinux2010_i686.whl',
            '{package_name}-{package_version}-cp27-cp27mu-manylinux2010_i686.whl',
            '{package_name}-{package_version}-cp35-cp35m-manylinux2010_i686.whl',
            '{package_name}-{package_version}-cp36-cp36m-manylinux2010_i686.whl',
            '{package_name}-{package_version}-cp37-cp37m-manylinux2010_i686.whl',
            '{package_name}-{package_version}-cp38-cp38-manylinux2010_i686.whl',
        ]
    elif platform == 'windows':
        templates = [
            '{package_name}-{package_version}-cp27-cp27m-win32.whl',
            '{package_name}-{package_version}-cp35-cp35m-win32.whl',
            '{package_name}-{package_version}-cp36-cp36m-win32.whl',
            '{package_name}-{package_version}-cp37-cp37m-win32.whl',
            '{package_name}-{package_version}-cp38-cp38-win32.whl',
            '{package_name}-{package_version}-cp27-cp27m-win_amd64.whl',
            '{package_name}-{package_version}-cp35-cp35m-win_amd64.whl',
            '{package_name}-{package_version}-cp36-cp36m-win_amd64.whl',
            '{package_name}-{package_version}-cp37-cp37m-win_amd64.whl',
            '{package_name}-{package_version}-cp38-cp38-win_amd64.whl',
        ]
    elif platform == 'macos':
        templates = [
            '{package_name}-{package_version}-cp27-cp27m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp35-cp35m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp36-cp36m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp37-cp37m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp38-cp38-macosx_10_9_x86_64.whl',
        ]
    else:
        raise Exception('unsupported platform')

    if IS_WINDOWS_RUNNING_ON_TRAVIS:
        # Python 2.7 isn't supported on Travis.
        templates = [t for t in templates if '-cp27-' not in t]

    return [filename.format(package_name=package_name, package_version=package_version)
            for filename in templates]

platform = None

if 'CIBW_PLATFORM' in os.environ:
    platform = os.environ['CIBW_PLATFORM']
elif sys.platform.startswith('linux'):
    platform = 'linux'
elif sys.platform.startswith('darwin'):
    platform = 'macos'
elif sys.platform in ['win32', 'cygwin']:
    platform = 'windows'
else:
    raise Exception('Unsupported platform')
