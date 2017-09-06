#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil, json
from glob import glob

import run_test

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    ### run the unit tests

    subprocess.check_call(['python', '-m', 'pytest', 'unit_test'])

    ### run the integration tests

    test_projects = glob('test/??_*')

    if len(test_projects) == 0:
        print('No test projects found. Aborting.', file=sys.stderr)
        exit(2)

    print('Testing projects:', test_projects)

    for project_path in test_projects:
        run_test.single_run(project_path)

    print('%d projects built successfully.' % len(test_projects))
