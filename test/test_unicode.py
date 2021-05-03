import textwrap

import pytest

from . import test_projects, utils

project_with_unicode = test_projects.new_c_project(
    spam_c_function_add=textwrap.dedent(
        r"""
        {
            Py_XDECREF(PyUnicode_FromStringAndSize("foo", 4));
        }
        """
    ),
)


def test(tmp_path):
    if utils.platform != "linux":
        pytest.skip("the docker test is only relevant to the linux build")

    project_dir = tmp_path / "project"
    project_with_unicode.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir, add_env={"CIBW_TEST_COMMAND": 'python -c "import spam"'}
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
