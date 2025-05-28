#!/usr/bin/env python3


import argparse
import functools
import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    if sys.version_info < (3, 13):
        default_cpu_count = os.cpu_count() or 2
    else:
        default_cpu_count = os.process_cpu_count() or 2

    make_parser = functools.partial(argparse.ArgumentParser, allow_abbrev=False)
    if sys.version_info >= (3, 14):
        make_parser = functools.partial(make_parser, color=True, suggest_on_error=True)
    parser = make_parser()
    parser.add_argument(
        "--run-podman", action="store_true", default=False, help="run podman tests (linux only)"
    )
    parser.add_argument(
        "--num-processes",
        action="store",
        default=default_cpu_count,
        help="number of processes to use for testing",
    )
    args = parser.parse_args()

    # move cwd to the project root
    os.chdir(Path(__file__).resolve().parents[1])

    # unit tests
    unit_test_args = [sys.executable, "-m", "pytest", "unit_test"]

    if sys.platform.startswith("linux") and os.environ.get("CIBW_PLATFORM", "linux") == "linux":
        # run the docker unit tests only on Linux
        unit_test_args += ["--run-docker"]

        if args.run_podman:
            unit_test_args += ["--run-podman"]

    print(
        "\n\n================================== UNIT TESTS ==================================",
        flush=True,
    )
    subprocess.run(unit_test_args, check=True)

    # Run the serial integration tests without multiple processes
    serial_integration_test_args = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "serial",
        "-x",
        "--durations",
        "0",
        "--timeout=2400",
        "test",
        "-vv",
    ]
    print(
        "\n\n=========================== SERIAL INTEGRATION TESTS ===========================",
        flush=True,
    )
    subprocess.run(serial_integration_test_args, check=True)

    # Non-serial integration tests
    integration_test_args = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "not serial",
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

    print(
        "\n\n========================= NON-SERIAL INTEGRATION TESTS =========================",
        flush=True,
    )
    subprocess.run(integration_test_args, check=True)
