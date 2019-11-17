#!/usr/bin/env python

from __future__ import print_function
import os, sys, subprocess, shutil, json
from glob import glob

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    ### run the unit tests

    subprocess.check_call([sys.executable, '-m', 'pytest', 'unit_test'])

    ### run the integration tests

    test_projects = [os.path.dirname(x) for x in sorted(glob('test/*/cibuildwheel_test.py'))]

    if len(test_projects) == 0:
        print('No test projects found. Aborting.', file=sys.stderr)
        exit(2)

    print('Testing projects:', test_projects)

    run_test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_test.py')
    test_failed = 0
    for project_path in test_projects:
        if 0 != subprocess.call([sys.executable, run_test_path, project_path]):
            test_failed += 1

    if test_failed > 0:
        print('%d of %d projects built failed.' % (test_failed, len(test_projects)))
        sys.exit(3)
    print('%d projects built successfully.' % len(test_projects))
