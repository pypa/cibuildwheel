#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys


def single_run(test_project):
    # run the test
    subprocess.check_call(
        [sys.executable, '-m', 'pytest', '-vvs', os.path.join(test_project, 'cibuildwheel_test.py')],
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("test_project_dir")
    args = parser.parse_args()

    project_path = os.path.abspath(args.test_project_dir)

    if not os.path.exists(project_path):
        print('No test project not found.', file=sys.stderr)
        exit(2)

    single_run(project_path)
