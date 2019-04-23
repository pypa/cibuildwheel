#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil

project_root = os.path.dirname(os.path.dirname(__file__))
test_utils_dir = os.path.join(project_root, 'test', 'shared')

def single_run(test_project):
    # set up an environment that gives access to the test utils
    env = os.environ.copy()

    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] += os.pathsep + test_utils_dir
    else:
        env['PYTHONPATH'] = test_utils_dir

    # run the test
    subprocess.check_call(
        [sys.executable, '-m', 'pytest', '-v', os.path.join(test_project, 'cibuildwheel_test.py')],
        env=env,
    )

    # clean up
    if os.path.exists('wheelhouse'):
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
