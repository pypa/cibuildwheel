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

    # run the integration tests
    subprocess.check_call([sys.executable, '-m', 'pytest', '-x', '--durations', '0', '--timeout=1200', 'test'])
