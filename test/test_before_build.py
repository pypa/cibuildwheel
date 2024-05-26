from __future__ import annotations

import subprocess
import textwrap

import pytest

from . import test_projects, utils

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import os

        # assert that the Python version as written to pythonversion_bb.txt in the CIBW_BEFORE_BUILD step
        # is the same one as is currently running.
        with open('pythonversion_bb.txt') as f:
            stored_version = f.read()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

        # check that the prefix also was written
        with open('pythonprefix_bb.txt') as f:
            stored_prefix = f.read()
        print('stored_prefix', stored_prefix)
        print('sys.prefix', sys.prefix)
        #  Works around path-comparison bugs caused by short-paths on Windows e.g.
        #  vssadm~1 instead of vssadministrator

        assert os.path.samefile(stored_prefix, sys.prefix)
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_before_build_asserts.generate(project_dir)

    before_build = (
        """python -c "import sys; open('{project}/pythonversion_bb.txt', 'w').write(sys.version)" && """
        '''python -c "import sys; open('{project}/pythonprefix_bb.txt', 'w').write(sys.prefix)"'''
    )

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # write python version information to a temporary file, this is
            # checked in setup.py
            "CIBW_BEFORE_BUILD": before_build,
        },
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_command(tmp_path):
    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_BEFORE_BUILD": "false",
                "CIBW_BEFORE_BUILD_WINDOWS": "exit /b 1",
            },
        )


def test_cwd(tmp_path):
    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BEFORE_BUILD": f'''python -c "import os; assert os.getcwd() == {str(project_dir)!r}"''',
            "CIBW_BEFORE_BUILD_LINUX": '''python -c "import os; assert os.getcwd() == '/project'"''',
        },
    )

    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
