#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil, json
from glob import glob

def single_run(test_project):
    # load project settings into environment
    env_file = os.path.join(test_project, 'environment.json')
    project_env = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            project_env = json.load(f)

    # run the build
    env = os.environ.copy()
    project_env = {str(k): str(v) for k, v in project_env.items()} # unicode not allowed in env
    env.update(project_env)
    print('Building %s with environment %s' % (test_project, project_env))
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', test_project], env=env)
    wheels = glob('wheelhouse/*.whl')
    print('%s built successfully. %i wheels built.' % (test_project, len(wheels)))

    # check some wheels were actually built
    assert len(wheels) >= 3

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

    print('Project built successfully.')
