#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    # run the unit tests
    unit_test_args = [sys.executable, '-m', 'pytest', 'unit_test']
    # run the docker unit tests only on Linux
    if sys.platform.startswith('linux'):
        unit_test_args += ['--run-docker']
    subprocess.check_call(unit_test_args)

    subprocess.check_call([sys.executable, '-m', 'pytest', '-x', '--durations', '0', 'test/test_0_basic.py', '-n0'])
    # run the integration tests
    subprocess.check_call([sys.executable, '-m', 'pytest', '-x', '--durations', '0', 'test', '-n', '2', '--dist=loadfile', '--ignore="test/test_0_basic.py"', '--ignore="test/test_dependency_versions.py"'])

    subprocess.check_call([sys.executable, '-m', 'pytest', '-x', '--durations', '0', 'test/test_dependency_versions.py', '-n0'])
