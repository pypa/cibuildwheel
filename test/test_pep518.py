import os
import textwrap

from . import test_projects, utils

basic_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        """
        # Will fail if PEP 518 does work
        import sys
        import requests
        if sys.version_info < (3, 6, 0):
            assert requests.__version__ == "2.22.0", "Requests found but wrong version ({0})".format(requests.__version__)
        else:
            assert requests.__version__ == "2.23.0", "Requests found but wrong version ({0})".format(requests.__version__)

        # Just making sure environment is still set
        import os
        if os.environ.get("CIBUILDWHEEL", "0") != "1":
            raise Exception("CIBUILDWHEEL environment variable is not set to 1")
        """
    )
)

basic_project.files[
    "pyproject.toml"
] = """
[build-system]
requires = [
    "setuptools >= 42",
    "setuptools_scm[toml]>=4.1.2",
    "wheel",
    "requests==2.22.0; python_version<'3.6'",
    "requests==2.23.0; python_version>='3.6'"
]

build-backend = "setuptools.build_meta"
"""


def test_pep518(tmp_path):

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)

    # These checks ensure an extra file is not created when using custom
    # workaround; see https://github.com/joerick/cibuildwheel/issues/421
    assert not (project_dir / "42").exists()
    assert not (project_dir / "4.1.2").exists()

    assert len(os.listdir(project_dir)) == len(basic_project.files)
