'''
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
'''

import subprocess, sys, os

IS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')


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


def cibuildwheel_run(project_path, env=None, add_env=None):
    '''
    Runs cibuildwheel as a subprocess, building the project at project_path. 
    
    Uses the current Python interpreter.
    Configure settings using env.
    '''
    if env is None:
        env = os.environ.copy()
    
    if add_env is not None:
        env.update(add_env)

    subprocess.check_call(
        [sys.executable, '-m', 'cibuildwheel', project_path],
        env=env,
    )


def expected_wheels(package_name, package_version, manylinux_versions={'1_x86_64', '2010_x86_64'}):
    '''
    Returns a list of expected wheels from a run of cibuildwheel.
    '''
    if platform == 'linux':
        templates = []
        if '1_x86_64' in manylinux_versions:
            templates += [
                '{package_name}-{package_version}-cp27-cp27m-manylinux1_x86_64.whl',
                '{package_name}-{package_version}-cp27-cp27mu-manylinux1_x86_64.whl',
                '{package_name}-{package_version}-cp34-cp34m-manylinux1_x86_64.whl',
                '{package_name}-{package_version}-cp35-cp35m-manylinux1_x86_64.whl',
                '{package_name}-{package_version}-cp36-cp36m-manylinux1_x86_64.whl',
                '{package_name}-{package_version}-cp37-cp37m-manylinux1_x86_64.whl',
            ]
        if '1_i686' in manylinux_versions:
            templates += [
                '{package_name}-{package_version}-cp27-cp27m-manylinux1_i686.whl',
                '{package_name}-{package_version}-cp27-cp27mu-manylinux1_i686.whl',
                '{package_name}-{package_version}-cp34-cp34m-manylinux1_i686.whl',
                '{package_name}-{package_version}-cp35-cp35m-manylinux1_i686.whl',
                '{package_name}-{package_version}-cp36-cp36m-manylinux1_i686.whl',
                '{package_name}-{package_version}-cp37-cp37m-manylinux1_i686.whl',
            ]
        if '2010_x86_64' in manylinux_versions:
            templates += [
                '{package_name}-{package_version}-cp27-cp27m-manylinux2010_x86_64.whl',
                '{package_name}-{package_version}-cp27-cp27mu-manylinux2010_x86_64.whl',
                '{package_name}-{package_version}-cp34-cp34m-manylinux2010_x86_64.whl',
                '{package_name}-{package_version}-cp35-cp35m-manylinux2010_x86_64.whl',
                '{package_name}-{package_version}-cp36-cp36m-manylinux2010_x86_64.whl',
                '{package_name}-{package_version}-cp37-cp37m-manylinux2010_x86_64.whl',
            ]
    elif platform == 'windows':
        templates = [
            '{package_name}-{package_version}-cp27-cp27m-win32.whl',
            '{package_name}-{package_version}-cp34-cp34m-win32.whl',
            '{package_name}-{package_version}-cp35-cp35m-win32.whl',
            '{package_name}-{package_version}-cp36-cp36m-win32.whl',
            '{package_name}-{package_version}-cp37-cp37m-win32.whl',
            '{package_name}-{package_version}-cp27-cp27m-win_amd64.whl',
            '{package_name}-{package_version}-cp34-cp34m-win_amd64.whl',
            '{package_name}-{package_version}-cp35-cp35m-win_amd64.whl',
            '{package_name}-{package_version}-cp36-cp36m-win_amd64.whl',
            '{package_name}-{package_version}-cp37-cp37m-win_amd64.whl',
        ]
    elif platform == 'macos':
        templates = [
            '{package_name}-{package_version}-cp27-cp27m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp34-cp34m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp35-cp35m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp36-cp36m-macosx_10_6_intel.whl',
            '{package_name}-{package_version}-cp37-cp37m-macosx_10_6_intel.whl',
        ]
    else:
        raise Exception('unsupported platform')
    
    if IS_RUNNING_ON_AZURE:
        # Python 3.4 isn't supported on Azure.
        templates = [t for t in templates if '-cp34-' not in t]
    
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
