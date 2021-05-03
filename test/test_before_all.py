import subprocess
import textwrap

import pytest

from . import test_projects, utils

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        # assert that the Python version as written to text_info.txt in the CIBW_BEFORE_ALL step
        # is the same one as is currently running.
        with open("text_info.txt") as f:
            stored_text = f.read()

        print("## stored text: " + stored_text)
        assert stored_text == "sample text 123"
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_before_build_asserts.generate(project_dir)

    with (project_dir / "text_info.txt").open(mode="w") as ff:
        print("dummy text", file=ff)

    # build the wheels
    before_all_command = '''python -c "import os;open('{project}/text_info.txt', 'w').write('sample text '+os.environ.get('TEST_VAL', ''))"'''
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            # write python version information to a temporary file, this is
            # checked in setup.py
            "CIBW_BEFORE_ALL": before_all_command,
            "CIBW_BEFORE_ALL_LINUX": f'{before_all_command} && python -c "import sys; assert sys.version_info >= (3, 6)"',
            "CIBW_ENVIRONMENT": "TEST_VAL='123'",
        },
    )

    # also check that we got the right wheels
    (project_dir / "text_info.txt").unlink()
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
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
    )

    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
