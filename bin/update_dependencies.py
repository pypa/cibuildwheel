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

os.chdir(DIR.parent)

subprocess.run(
    [
        "pip-compile",
        "--allow-unsafe",
        "--upgrade",
        "cibuildwheel/resources/constraints.in",
        f"--output-file=cibuildwheel/resources/constraints-python{python_version}.txt",
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
