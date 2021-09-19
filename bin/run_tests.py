#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    # run the unit tests
    unit_test_args = [sys.executable, "-m", "pytest", "unit_test"]
    # run the docker unit tests only on Linux
    if sys.platform.startswith("linux"):
        unit_test_args += ["--run-docker"]
    subprocess.run(unit_test_args, check=True)

    # run the integration tests
    xdist_test_args = []
    if sys.platform.startswith("linux"):
        xdist_test_args = ["-n", "2"]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *xdist_test_args,
            "-x",
            "--durations",
            "0",
            "--timeout=2400",
            "test",
        ],
        check=True,
    )
