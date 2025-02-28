import textwrap

from . import test_projects, utils

project_with_skip_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        rf"""
        if sys.implementation.name != "cpython":
            raise Exception("Only CPython shall be built")
        expected_version = {"({}, {})".format(*utils.SINGLE_PYTHON_VERSION)}
        if sys.version_info[0:2] != expected_version:
            raise Exception("CPython {{}}.{{}} should be skipped".format(*sys.version_info[0:2]))
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_skip_asserts.generate(project_dir)

    skip = " ".join(
        f"cp3{minor}-*" for minor in range(6, 30) if (3, minor) != utils.SINGLE_PYTHON_VERSION
    )

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp3*-*",
            "CIBW_SKIP": f"*t-* {skip}",
        },
    )

    # check that we got the right wheels. There should be a single version of CPython.
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)
