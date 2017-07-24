#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil, json, argparse
from glob import glob

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("test_project_dir")
    args = parser.parse_args()

    test_project = os.path.abspath(args.test_project_dir)

    # move cwd to the project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if not os.path.exists(test_project):
        print('No test project not found.', file=sys.stderr)
        exit(2)

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
    subprocess.check_call(['cibuildwheel', test_project], env=env)
    wheels = glob('wheelhouse/*.whl')
    print('%s built successfully. %i wheels built.' % (test_project, len(wheels)))

    # check some wheels were actually built
    assert len(wheels) >= 4

    # clean up
    shutil.rmtree('wheelhouse')

    print('Project built successfully.')

main()
