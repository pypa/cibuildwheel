import subprocess
import textwrap

import pytest

from . import test_projects, utils

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import os

        # assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_BUILD step
        # is the same one as is currently running.
        version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
        with open(version_file) as f:
            stored_version = f.read()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

        # check that the executable also was written
        executable_file = 'c:\\pythonexecutable.txt' if sys.platform == 'win32' else '/tmp/pythonexecutable.txt'
        with open(executable_file) as f:
            stored_executable = f.read()
        print('stored_executable', stored_executable)
        print('sys.executable', sys.executable)

        # windows/mac are case insensitive
        stored_path = os.path.realpath(stored_executable).lower()
        current_path = os.path.realpath(sys.executable).lower()

        # TODO: This is not valid in an virtual environment
        assert stored_path == current_path, '{0} != {1}'.format(stored_path, current_path)
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_before_build_asserts.generate(project_dir)

    before_build = (
        """python -c "import sys; open('{output_dir}pythonversion.txt', 'w').write(sys.version)" && """
        '''python -c "import sys; open('{output_dir}pythonexecutable.txt', 'w').write(sys.executable)"'''
    )

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # write python version information to a temporary file, this is
            # checked in setup.py
            "CIBW_BEFORE_BUILD": before_build.format(output_dir="/tmp/"),
            "CIBW_BEFORE_BUILD_WINDOWS": before_build.format(output_dir=r"c:\\"),
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
