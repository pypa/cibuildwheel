from __future__ import annotations

import platform
import re
import textwrap
from pathlib import Path

import pytest

import cibuildwheel.util

from . import test_projects, utils

project_with_expected_version_checks = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import subprocess
        import os
        import sys

        versions_output_text = subprocess.check_output(
            [sys.executable, '-m', 'pip', 'freeze', '--all', '-qq'],
            universal_newlines=True,
        )
        versions = versions_output_text.strip().splitlines()

        # `versions` now looks like:
        # ['pip==x.x.x', 'setuptools==x.x.x', 'wheel==x.x.x']

        print('Gathered versions', versions)

        expected_version = os.environ['EXPECTED_PIP_VERSION']

        assert f'pip=={expected_version}' in versions, (
            f'error: pip version should equal {expected_version}'
        )
        """
    )
)

project_with_expected_version_checks.files["pyproject.toml"] = r"""
[build-system]
requires = ["setuptools", "pip"]
build-backend = "setuptools.build_meta"
"""

VERSION_REGEX = r"([\w-]+)==([^\s]+)"


def get_versions_from_constraint_file(constraint_file: Path) -> dict[str, str]:
    constraint_file_text = constraint_file.read_text(encoding="utf-8")

    return dict(re.findall(VERSION_REGEX, constraint_file_text))


@pytest.mark.parametrize("python_version", ["3.6", "3.8", "3.12"])
def test_pinned_versions(tmp_path, python_version, build_frontend_env_nouv):
    if utils.platform == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")
    if python_version == "3.6" and utils.platform == "macos" and platform.machine() == "arm64":
        pytest.skip("macOS arm64 does not support Python 3.6")
    if python_version != "3.12" and utils.platform == "pyodide":
        pytest.skip(f"pyodide does not support Python {python_version}")

    project_dir = tmp_path / "project"
    project_with_expected_version_checks.generate(project_dir)

    version_no_dot = python_version.replace(".", "")
    build_environment = {}
    build_pattern = f"[cp]p{version_no_dot}-*"
    constraint_filename = f"constraints-python{version_no_dot}.txt"
    constraint_file = cibuildwheel.util.resources_dir / constraint_filename
    constraint_versions = get_versions_from_constraint_file(constraint_file)

    build_environment["EXPECTED_PIP_VERSION"] = constraint_versions["pip"]

    cibw_environment_option = " ".join(f"{k}={v}" for k, v in build_environment.items())

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": build_pattern,
            "CIBW_ENVIRONMENT": cibw_environment_option,
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


def test_dependency_constraints_file(tmp_path, build_frontend_env_nouv):
    if utils.platform == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")

    project_dir = tmp_path / "project"
    project_with_expected_version_checks.generate(project_dir)

    tool_versions = {
        "pip": "23.1.2",
        "delocate": "0.10.3",
    }

    constraints_file = tmp_path / "constraints file.txt"
    constraints_file.write_text(
        textwrap.dedent(
            """
            pip=={pip}
            delocate=={delocate}
            """.format(**tool_versions)
        )
    )

    build_environment = {}

    for package_name, version in tool_versions.items():
        env_name = f"EXPECTED_{package_name.upper()}_VERSION"
        build_environment[env_name] = version

    cibw_environment_option = " ".join(f"{k}={v}" for k, v in build_environment.items())

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ENVIRONMENT": cibw_environment_option,
            "CIBW_DEPENDENCY_VERSIONS": str(constraints_file),
            "CIBW_SKIP": "cp36-*",
            **build_frontend_env_nouv,
        },
    )

    # also check that we got the right wheels
    expected_wheels = [w for w in utils.expected_wheels("spam", "0.1.0") if "-cp36" not in w]

    assert set(actual_wheels) == set(expected_wheels)
