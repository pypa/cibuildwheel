#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == '__main__':
    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    parser = argparse.ArgumentParser(description='Runs a sample build')
    parser.add_argument('project_python_path', nargs='?', default='test.test_0_basic.basic_project')

    options = parser.parse_args()

    project_dir = tempfile.mkdtemp()
    subprocess.run([
        sys.executable, '-m', 'test.test_projects',
        options.project_python_path, project_dir
    ], check=True)

    sys.exit(subprocess.run([sys.executable, '-m', 'cibuildwheel'], cwd=project_dir).returncode)
