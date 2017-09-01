#!/usr/bin/python

from __future__ import print_function
import os, sys, subprocess, shutil, json
from glob import glob

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
    # load project settings into environment
    env_file = os.path.join(project_path, 'environment.json')
    project_env = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            project_env = json.load(f)

    # run the build
    env = os.environ.copy()
    project_env = {str(k): str(v) for k, v in project_env.items()} # unicode not allowed in env
    env.update(project_env)
    print('Building %s with environment %s' % (project_path, project_env))
    subprocess.check_call(['cibuildwheel', project_path], env=env)
    wheels = glob('wheelhouse/*.whl')
    print('%s built successfully. %i wheels built.' % (project_path, len(wheels)))

    # check some wheels were actually built
    assert len(wheels) >= 4

    # clean up
    shutil.rmtree('wheelhouse')

print('%d projects built successfully.' % len(test_projects))
