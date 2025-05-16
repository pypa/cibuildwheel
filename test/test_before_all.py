import subprocess
import textwrap

import pytest

from . import test_projects, utils

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import os

        with open("text_info.txt") as f:
            stored_text = f.read()
        print("## stored text: " + stored_text)
        assert stored_text == "sample text 123"

        # assert that the Python version as written to python_prefix.txt in the CIBW_BEFORE_ALL step
        # is not the same one as is currently running.
        with open('python_prefix.txt') as f:
            stored_prefix = f.read()
        print('stored_prefix', stored_prefix)
        print('sys.prefix', sys.prefix)
        #  Works around path-comparison bugs caused by short-paths on Windows e.g.
        #  vssadm~1 instead of vssadministrator
        assert not os.path.samefile(stored_prefix, sys.prefix)
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_before_build_asserts.generate(project_dir)

    with (project_dir / "text_info.txt").open(mode="w") as ff:
        print("dummy text", file=ff)

    # write python version information to a temporary file, this is checked in
    # setup.py
    #
    # note, before_all runs in whatever the host environment is, `python`
    # might be any version of python (even Python 2 on Travis ci!), so this is
    # written to be broadly compatible
    before_all_command = (
        """python -c "import os, sys; f = open('{project}/text_info.txt', 'w'); f.write('sample text '+os.environ.get('TEST_VAL', '')); f.close()" && """
        '''python -c "import sys; f = open('{project}/python_prefix.txt', 'w'); f.write(sys.prefix); f.close()"'''
    )
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BEFORE_ALL": before_all_command,
            "CIBW_BEFORE_ALL_LINUX": f'{before_all_command} && python -c "import sys; assert sys.version_info >= (3, 8)"',
            "CIBW_ENVIRONMENT": "TEST_VAL='123'",
        },
        single_python=True,
    )

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)


def test_failing_command(tmp_path):
    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_BEFORE_ALL": "false",
                "CIBW_BEFORE_ALL_WINDOWS": "exit /b 1",
            },
        )


def test_cwd(tmp_path):
    project_dir = tmp_path / "project"
    test_projects.new_c_project().generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BEFORE_ALL": f'''python -c "import os; assert os.getcwd() == {str(project_dir)!r}"''',
            "CIBW_BEFORE_ALL_LINUX": '''python -c "import os; assert os.getcwd() == '/project'"''',
        },
        single_python=True,
    )

    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)
