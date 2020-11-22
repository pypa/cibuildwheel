#!/usr/bin/env python3

import os
import subprocess
import sys
import argparse
import tempfile
from pathlib import Path

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    parser = argparse.ArgumentParser(description='Runs a sample build')
    parser.add_argument('PROJECT_PYTHON_PATH', nargs='?', default='test.test_0_basic.basic_project')

    options = parser.parse_args()
    print(options)

    project_dir = tempfile.mkdtemp()
    subprocess.run([sys.executable, '-m', 'test.test_projects', options.PROJECT_PYTHON_PATH, project_dir], check=True)

    subprocess.run(['cibuildwheel'], check=True, cwd=project_dir)
