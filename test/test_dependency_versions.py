import json
import platform
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

from cibuildwheel.util import resources

from . import test_projects, utils

VERSION_REGEX = r"([\w-]+)==([^\s]+)"

CHECK_VERSIONS_SCRIPT = """\
'''
Checks that the versions in the env var EXPECTED_VERSIONS match those
installed in the active venv.
'''
import os, subprocess, sys, json

versions_raw = json.loads(
    subprocess.check_output([
        sys.executable, '-m', 'pip', 'list', '--format=json',
    ], text=True)
)
versions = {item['name']: item['version'] for item in versions_raw}
expected_versions = json.loads(os.environ['EXPECTED_VERSIONS'])

for name, expected_version in expected_versions.items():
    if name not in versions:
        continue
    if versions[name] != expected_version:
        raise SystemExit(f'error: {name} version should equal {expected_version}. Versions: {versions}')
"""


def test_check_versions_script(tmp_path, build_frontend_env_nouv, capfd):
    if utils.get_platform() == "linux":
        pytest.skip("we don't test dependency versions on linux, refer to other tests")

    # sanity check that the CHECK_VERSIONS_SCRIPT fails when it should
    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    expected_versions = {
        "pip": "0.0.1",
        "build": "0.0.2",
    }
    script = project_dir / "check_versions.py"
    script.write_text(CHECK_VERSIONS_SCRIPT)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_BEFORE_BUILD": f"python {script.name}",
                "EXPECTED_VERSIONS": json.dumps(expected_versions),
                **build_frontend_env_nouv,
            },
        )

    captured = capfd.readouterr()

    assert (
        "error: pip version should equal 0.0.1" in captured.err
        or "error: build version should equal 0.0.2" in captured.err
    )


def get_versions_from_constraint_file(constraint_file: Path) -> dict[str, str]:
    constraint_file_text = constraint_file.read_text(encoding="utf-8")

    return dict(re.findall(VERSION_REGEX, constraint_file_text))


@pytest.mark.parametrize("python_version", ["3.8", "3.12"])
def test_pinned_versions(tmp_path, python_version, build_frontend_env_nouv):
    if utils.get_platform() == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")
    if python_version != "3.12" and utils.get_platform() == "pyodide":
        pytest.skip(f"pyodide does not support Python {python_version}")
    if (
        python_version == "3.8"
        and utils.get_platform() == "windows"
        and platform.machine() == "ARM64"
    ):
        pytest.skip(f"Windows ARM64 does not support Python {python_version}")

    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    # read the expected versions from the appropriate constraint file
    version_no_dot = python_version.replace(".", "")

    # create cross-platform Python before-build script to verify versions pre-build
    before_build_script = project_dir / "check_versions.py"
    before_build_script.write_text(CHECK_VERSIONS_SCRIPT)

    if utils.get_platform() == "pyodide":
        constraint_filename = f"constraints-pyodide{version_no_dot}.txt"
    else:
        constraint_filename = f"constraints-python{version_no_dot}.txt"
    constraint_file = resources.PATH / constraint_filename
    constraint_versions = get_versions_from_constraint_file(constraint_file)

    # build and test the wheels (dependency version check occurs before-build)
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": f"[cp]p{version_no_dot}-*",
            "CIBW_BEFORE_BUILD": f"python {before_build_script.name}",
            "EXPECTED_VERSIONS": json.dumps(constraint_versions),
            **build_frontend_env_nouv,
        },
    )

    # also check that we got the right wheels
    expected_wheels = [
        w
        for w in utils.expected_wheels("spam", "0.1.0")
        if f"-cp{version_no_dot}" in w or f"-pp{version_no_dot}" in w
    ]

    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.parametrize("method", ["inline", "file"])
def test_dependency_constraints(method, tmp_path, build_frontend_env_nouv):
    if utils.get_platform() == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")

    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    tool_versions = {
        "pip": "23.1.2",
        "build": "1.2.2",
        "delocate": "0.10.3",
    }

    if method == "file":
        constraints_file = tmp_path / "constraints file.txt"
        constraints_file.write_text(
            textwrap.dedent(
                """
                pip=={pip}
                build=={build}
                delocate=={delocate}
                """.format(**tool_versions)
            )
        )
        dependency_version_option = str(constraints_file)
    elif method == "inline":
        dependency_version_option = "packages: " + " ".join(
            f"{k}=={v}" for k, v in tool_versions.items()
        )
    else:
        msg = f"Unknown method: {method}"
        raise ValueError(msg)

    skip = ""

    if (
        utils.get_platform() == "windows"
        and method == "file"
        and build_frontend_env_nouv["CIBW_BUILD_FRONTEND"] == "build"
    ):
        # GraalPy 24 fails to discover its standard library when a venv is created
        # from a virtualenv seeded executable. See
        # https://github.com/oracle/graalpython/issues/491 and remove this once
        # GraalPy 24 is dropped
        skip = "gp311*"

    # cross-platform Python script for dependency constraint checks
    before_build_script = project_dir / "check_versions.py"
    before_build_script.write_text(CHECK_VERSIONS_SCRIPT)

    # build and test the wheels (dependency version check occurs pre-build)
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_SKIP": skip,
            "CIBW_DEPENDENCY_VERSIONS": dependency_version_option,
            "CIBW_BEFORE_BUILD": f"python {before_build_script.name}",
            "EXPECTED_VERSIONS": json.dumps(tool_versions),
            **build_frontend_env_nouv,
        },
        single_python=True,
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)

    if skip == "gp*":
        # See reference to https://github.com/oracle/graalpython/issues/491
        # above
        expected_wheels = [w for w in expected_wheels if "graalpy311" not in w]

    assert set(actual_wheels) == set(expected_wheels)
