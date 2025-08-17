#!/usr/bin/env python3


import argparse
import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    if sys.version_info < (3, 13):
        default_cpu_count = os.cpu_count() or 2
    else:
        default_cpu_count = os.process_cpu_count() or 2

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--run-podman", action="store_true", default=False, help="run podman tests (linux only)"
    )
    parser.add_argument(
        "--num-processes",
        action="store",
        default=default_cpu_count,
        help="number of processes to use for testing",
    )
    parser.add_argument(
        "--test-select",
        choices={"all", "native", "android", "ios", "pyodide"},
        default="all",
        help="Either 'native' or 'android'/'ios'/'pyodide'",
    )
    args = parser.parse_args()

    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    # doc tests
    doc_test_args = [sys.executable, "-m", "pytest", "cibuildwheel"]

    print(
        "\n\n================================== DOC TESTS ==================================",
        flush=True,
    )
    result = subprocess.run(doc_test_args, check=False)
    if result.returncode not in (0, 5):
        # Allow case where no doctests are collected (returncode 5) because
        # circleci sets an explicit "-k" filter that disables doctests. There
        # isn't a pattern that will only select doctests. This can be removed
        # and have check=True if the circleci PYTEST_ADDOPTS is removed.
        raise subprocess.CalledProcessError(
            result.returncode, result.args, output=result.stdout, stderr=result.stderr
        )

    # unit tests
    print(
        "\n\n================================== UNIT TESTS ==================================",
        flush=True,
    )
    unit_test_args = [sys.executable, "-m", "pytest", "unit_test"]

    if (
        sys.platform.startswith("linux")
        and os.environ.get("CIBW_PLATFORM", "linux") == "linux"
        and args.test_select in ["all", "native"]
    ):
        # run the docker unit tests only on Linux
        unit_test_args += ["--run-docker"]

        if args.run_podman:
            unit_test_args += ["--run-podman"]

    subprocess.run(unit_test_args, check=True)

    print(
        "\n\n=========================== SERIAL INTEGRATION TESTS ===========================",
        flush=True,
    )

    match args.test_select:
        case "all":
            marks = []
        case "native":
            marks = ["not pyodide", "not android", "not ios"]
        case mark:
            marks = [f"{mark}"]

    # Run the serial integration tests without multiple processes
    serial_integration_test_args = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        f"{' and '.join(['serial', *marks])}",
        "-x",
        "--durations",
        "0",
        "--timeout=2400",
        "test",
        "-vv",
    ]

    subprocess.run(serial_integration_test_args, check=True)

    print(
        "\n\n========================= NON-SERIAL INTEGRATION TESTS =========================",
        flush=True,
    )
    integration_test_args = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        f"{' and '.join(['not serial', *marks])}",
        f"--numprocesses={args.num_processes}",
        "-x",
        "--durations",
        "0",
        "--timeout=2400",
        "test",
        "-vv",
    ]

    if sys.platform.startswith("linux") and args.run_podman:
        integration_test_args += ["--run-podman"]

    subprocess.run(integration_test_args, check=True)
