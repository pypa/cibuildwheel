from __future__ import print_function
import os, sys, subprocess
from glob import glob

# move cwd to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

test_projects = glob('test/??_*')

if len(test_projects) == 0:
    print('No test projects found. Aborting.', file=sys.stderr)
    exit(2)

print('Testing projects:', test_projects)

for project_path in test_projects:
    subprocess.check_call(['cibuildwheel', project_path])
    print('%s built successfully.' % project_path)

print('%d projects built successfully.' % len(test_projects))
