'''
Utility functions used by the cibuildwheel tests.

This file is added to the PYTHONPATH in the test runner at bin/run_test.py.
'''

import subprocess, sys

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

platform = None

if sys.platform.startswith('linux'):
    platform = 'linux'
elif sys.platform.startswith('darwin'):
    platform = 'macos'
elif sys.platform in ['win32', 'cygwin']:
    platform = 'windows'
else:
    raise Exception('Unsupported platform')
