import re
import textwrap

import pytest

import cibuildwheel.util

from . import test_projects, utils

project_with_expected_version_checks = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import subprocess
        import os

        versions_output_text = subprocess.check_output(
            ['pip', 'freeze', '--all', '-qq'],
            universal_newlines=True,
        )
        versions = versions_output_text.strip().splitlines()

        # `versions` now looks like:
        # ['pip==x.x.x', 'setuptools==x.x.x', 'wheel==x.x.x']

        print('Gathered versions', versions)

        for package_name in ['pip', 'setuptools', 'wheel']:
            env_name = 'EXPECTED_{}_VERSION'.format(package_name.upper())
            expected_version = os.environ[env_name]

            assert '{}=={}'.format(package_name, expected_version) in versions, (
                'error: {} version should equal {}'.format(package_name, expected_version)
            )
        """
    )
)


VERSION_REGEX = r"([\w-]+)==([^\s]+)"


def get_versions_from_constraint_file(constraint_file):
    constraint_file_text = constraint_file.read_text(encoding="utf8")

    return {
        package: version for package, version in re.findall(VERSION_REGEX, constraint_file_text)
    }


@pytest.mark.parametrize("python_version", ["3.6", "3.8", "3.9"])
def test_pinned_versions(tmp_path, python_version, build_frontend_env):
    if utils.platform == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")

    project_dir = tmp_path / "project"
    project_with_expected_version_checks.generate(project_dir)

    build_environment = {}

    if python_version == "3.6":
        constraint_filename = "constraints-python36.txt"
        build_pattern = "[cp]p36-*"
    elif python_version == "3.7":
        constraint_filename = "constraints-python37.txt"
        build_pattern = "[cp]p37-*"
    elif python_version == "3.8":
        constraint_filename = "constraints-python38.txt"
        build_pattern = "[cp]p38-*"
    else:
        constraint_filename = "constraints.txt"
        build_pattern = "[cp]p39-*"

    constraint_file = cibuildwheel.util.resources_dir / constraint_filename
    constraint_versions = get_versions_from_constraint_file(constraint_file)

    for package in ["pip", "setuptools", "wheel", "virtualenv"]:
        env_name = f"EXPECTED_{package.upper()}_VERSION"
        build_environment[env_name] = constraint_versions[package]

    cibw_environment_option = " ".join(f"{k}={v}" for k, v in build_environment.items())

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": build_pattern,
            "CIBW_ENVIRONMENT": cibw_environment_option,
            **build_frontend_env,
        },
    )

    # also check that we got the right wheels
    if python_version == "3.6":
        expected_wheels = [
            w for w in utils.expected_wheels("spam", "0.1.0") if "-cp36" in w or "-pp36" in w
        ]
    elif python_version == "3.8":
        expected_wheels = [
            w for w in utils.expected_wheels("spam", "0.1.0") if "-cp38" in w or "-pp38" in w
        ]
    elif python_version == "3.9":
        expected_wheels = [
            w for w in utils.expected_wheels("spam", "0.1.0") if "-cp39" in w or "-pp39" in w
        ]
    else:
        raise ValueError("unhandled python version")

    assert set(actual_wheels) == set(expected_wheels)


def test_dependency_constraints_file(tmp_path, build_frontend_env):
    if utils.platform == "linux":
        pytest.skip("linux doesn't pin individual tool versions, it pins manylinux images instead")

    project_dir = tmp_path / "project"
    project_with_expected_version_checks.generate(project_dir)

    tool_versions = {
        "pip": "20.0.2",
        "setuptools": "53.0.0",
        "wheel": "0.34.2",
        "virtualenv": "20.0.35",
    }

    constraints_file = tmp_path / "constraints file.txt"
    constraints_file.write_text(
        textwrap.dedent(
            """
            pip=={pip}
            setuptools=={setuptools}
            wheel=={wheel}
            virtualenv=={virtualenv}
            importlib-metadata<3,>=0.12; python_version < "3.8"
            """.format(
                **tool_versions
            )
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
            **build_frontend_env,
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")

    assert set(actual_wheels) == set(expected_wheels)
