import textwrap

from . import test_projects, utils

project_with_skip_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        # explode if run on PyPyor Python 3.7 (these should be skipped)
        if sys.implementation.name != "cpython":
            raise Exception("Only CPython shall be built")
        if sys.version_info[0:2] == (3, 7):
            raise Exception("CPython 3.7 should be skipped")
        """
    )
)


def test(tmp_path):
    project_dir = tmp_path / "project"
    project_with_skip_asserts.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD": "cp3*-*",
            "CIBW_SKIP": "cp37-*",
        },
    )

    # check that we got the right wheels. There should be no PyPy or 3.7.
    expected_wheels = [
        w for w in utils.expected_wheels("spam", "0.1.0") if ("-cp3" in w) and ("-cp37" not in w)
    ]
    assert set(actual_wheels) == set(expected_wheels)
