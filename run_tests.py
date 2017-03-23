from __future__ import print_function
import os, sys, subprocess, shutil, json
from glob import glob

# move cwd to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

test_projects = glob('test/??_*')

if len(test_projects) == 0:
    print('No test projects found. Aborting.', file=sys.stderr)
    exit(2)

print('Testing projects:', test_projects)

for project_path in test_projects:
    # load project settings into environment
    env = os.environ.copy()
    env_file = os.path.join(project_path, 'environment.json')
    if os.path.exists(env_file):
        with open(env_file) as f:
            env.update(json.load(f))

    # run the build
    subprocess.check_call(['cibuildwheel', project_path], env=env)
    wheels = glob('wheelhouse/*.whl')
    print('%s built successfully. %i wheels built.' % (project_path, len(wheels)))

    # check wheels were actually built
    assert len(wheels) >= 4

    # clean up
    shutil.rmtree('wheelhouse')

print('%d projects built successfully.' % len(test_projects))
