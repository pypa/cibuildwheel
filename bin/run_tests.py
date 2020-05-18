#!/usr/bin/env python3

import os
import subprocess
import sys

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # run the unit tests
    subprocess.check_call([sys.executable, '-m', 'pytest', 'unit_test'])

    # run the integration tests
    subprocess.check_call([sys.executable, '-m', 'pytest', '-x', '--durations', '0', 'test'])
