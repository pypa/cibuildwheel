#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil

def single_run(test_project):
    # run the test
    subprocess.check_call(
        [sys.executable, '-m', 'pytest', '-v', os.path.join(test_project, 'cibuildwheel_test.py')]
    )

    # clean up
    shutil.rmtree('wheelhouse')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("test_project_dir")
    args = parser.parse_args()

    project_path = os.path.abspath(args.test_project_dir)
    
    if not os.path.exists(project_path):
        print('No test project not found.', file=sys.stderr)
        exit(2)

    single_run(project_path)
