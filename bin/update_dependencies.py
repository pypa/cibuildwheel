#!/usr/bin/env python3
# This file supports 3.6+

import os
import shutil
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "cibuildwheel/resources"

python_version = "".join(str(v) for v in sys.version_info[:2])

env = os.environ.copy()

# CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
# regenerate the constraints files
env["CUSTOM_COMPILE_COMMAND"] = "bin/update_dependencies.py"

if python_version == "36":
    # Bug with click and Python 3.6
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"

subprocess.run(
    [
        "pip-compile",
        "--allow-unsafe",
        "--upgrade",
        f"{RESOURCES}/constraints.in",
        f"--output-file={RESOURCES}/constraints-python{python_version}.txt",
    ],
    check=True,
    env=env,
)

# default constraints.txt
if python_version == "39":
    shutil.copyfile(
        RESOURCES / f"constraints-python{python_version}.txt",
        RESOURCES / "constraints.txt",
    )
