import importlib
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path


def main():
    parser = ArgumentParser(
        prog="python -m test.test_projects",
        description='Generate a test project to check it out'
    )
    parser.add_argument('PROJECT', help='''
        Python path to a project object. E.g. test.test_0_basic.basic_project
    ''')
    options = parser.parse_args()

    module, _, name = options.PROJECT.rpartition('.')

    project = getattr(importlib.import_module(module), name)

    project_dir = Path(tempfile.mkdtemp())
    project.generate(project_dir)

    print('Project generated at', project_dir)
    print()

    if sys.platform == 'darwin':
        subprocess.check_call(['open', '--', project_dir])
    elif sys.platform == 'linux2':
        subprocess.check_call(['xdg-open', '--', project_dir])
    elif sys.platform == 'win32':
        subprocess.check_call(['explorer', project_dir])


if __name__ == '__main__':
    main()
