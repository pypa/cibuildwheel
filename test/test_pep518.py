import textwrap

from . import test_projects, utils

basic_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        """
        # Will fail if PEP 518 does work
        import jmespath
        assert jmespath.__version__ == "0.10.0", "'jmespath' found but wrong version ({0})".format(jmespath.__version__)

        # Just making sure environment is still set
        import os
        if os.environ.get("CIBUILDWHEEL", "0") != "1":
            raise Exception("CIBUILDWHEEL environment variable is not set to 1")
        """
    )
)

basic_project.files["pyproject.toml"] = """
[build-system]
requires = [
    "setuptools >= 42",
    "setuptools_scm[toml]>=4.1.2",
    "jmespath==0.10.0"
]

build-backend = "setuptools.build_meta"
"""


def test_pep518(tmp_path, build_frontend_env):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # GraalPy fails to discover its standard library when a venv is created
    # from a virtualenv seeded executable. See
    # https://github.com/oracle/graalpython/issues/491 and remove this once
    # fixed upstream.
    if build_frontend_env["CIBW_BUILD_FRONTEND"] == "build" and utils.get_platform() == "windows":
        build_frontend_env["CIBW_SKIP"] = "gp*"

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=build_frontend_env)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0")

    # GraalPy fails to discover its standard library when a venv is created
    # from a virtualenv seeded executable. See
    # https://github.com/oracle/graalpython/issues/491 and remove this once
    # fixed upstream.
    if build_frontend_env["CIBW_BUILD_FRONTEND"] == "build" and utils.get_platform() == "windows":
        expected_wheels = [w for w in expected_wheels if "graalpy" not in w]

    assert set(actual_wheels) == set(expected_wheels)

    # These checks ensure an extra file is not created when using custom
    # workaround; see https://github.com/pypa/cibuildwheel/issues/421
    assert not (project_dir / "42").exists()
    assert not (project_dir / "4.1.2").exists()

    # pypa/build creates a "build" folder & a "*.egg-info" folder for the
    # wheel being built, this should be harmless so remove them. pyodide-build
    # creates a ".pyodide_build" folder, but this is gitignored with a
    # .gitignore file inside.
    contents = [
        item
        for item in project_dir.iterdir()
        if item.name != "build"
        and not item.name.endswith(".egg-info")
        and item.name != ".pyodide_build"
    ]

    print("Project contents after build:")
    print("\n".join(f"  {f}" for f in contents))

    assert len(contents) == len(basic_project.files)
