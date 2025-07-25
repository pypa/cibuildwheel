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
    match os.environ.get("CIBW_PLATFORM", "native"):
        case "":
            serial_integration_test_args += ["-m not pyodide", "-m not android", "-m not ios"]
        case "native":
            pass
        case platform:
            serial_integration_test_args += ["-m {platform}"]

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
