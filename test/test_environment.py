import os
import subprocess
import sys
import textwrap

import pytest

from . import test_projects, utils

project_with_environment_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import os

        # explode if environment isn't correct, as set in CIBW_ENVIRONMENT
        CIBW_TEST_VAR = os.environ.get("CIBW_TEST_VAR")
        CIBW_TEST_VAR_2 = os.environ.get("CIBW_TEST_VAR_2")
        CIBW_TEST_VAR_3 = os.environ.get("CIBW_TEST_VAR_3")
        PATH = os.environ.get("PATH")

        if CIBW_TEST_VAR != "a b c":
            raise Exception('CIBW_TEST_VAR should equal "a b c". It was "%s"' % CIBW_TEST_VAR)
        if CIBW_TEST_VAR_2 != "1":
            raise Exception('CIBW_TEST_VAR_2 should equal "1". It was "%s"' % CIBW_TEST_VAR_2)
        if CIBW_TEST_VAR_3 != "test string 3":
            raise Exception('CIBW_TEST_VAR_3 should equal "test string 3". It was "%s"' % CIBW_TEST_VAR_3)
        if "/opt/cibw_test_path" not in PATH:
            raise Exception('PATH should contain "/opt/cibw_test_path". It was "%s"' % PATH)
        if "$PATH" in PATH:
            raise Exception('$PATH should be expanded in PATH. It was "%s"' % PATH)
        """
    )
)


def test(tmp_path):
    python_echo = f"'{sys.executable}' -c \"import sys; print(*sys.argv[1:])\""
    project_dir = tmp_path / "project"
    project_with_environment_asserts.generate(project_dir)

    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup.py
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ENVIRONMENT": """CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH=$PATH:/opt/cibw_test_path""",
            "CIBW_ENVIRONMENT_WINDOWS": f'''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$({python_echo} 'test string 3')" PATH="$PATH;/opt/cibw_test_path"''',
        },
        single_python=True,
    )

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)


def test_overridden_path(tmp_path, capfd):
    project_dir = tmp_path / "project"
    output_dir = tmp_path / "output"

    project = test_projects.new_c_project()
    project.generate(project_dir)
    output_dir.mkdir()

    # mess up PATH, somehow
    if utils.get_platform() == "linux":
        with pytest.raises(subprocess.CalledProcessError):
            utils.cibuildwheel_run(
                project_dir,
                output_dir=output_dir,
                add_env={
                    "CIBW_BEFORE_ALL": "mkdir new_path && touch new_path/python && chmod +x new_path/python",
                    "CIBW_ENVIRONMENT": '''PATH="$(pwd)/new_path:$PATH"''',
                },
            )
    else:
        new_path = tmp_path / "another_bin"
        new_path.mkdir()
        (new_path / "python").touch(mode=0o777)

        with pytest.raises(subprocess.CalledProcessError):
            utils.cibuildwheel_run(
                project_dir,
                output_dir=output_dir,
                add_env={
                    "NEW_PATH": str(new_path),
                    "CIBW_ENVIRONMENT": f'''PATH="$NEW_PATH{os.pathsep}$PATH"''',
                },
            )

    assert len(list(output_dir.iterdir())) == 0
    captured = capfd.readouterr()
    assert "python available on PATH doesn't match our installed instance" in captured.err.replace(
        "venv", "installed"
    )


@pytest.mark.parametrize(
    "build_frontend",
    [
        pytest.param("pip", marks=utils.skip_if_pyodide("No pip for pyodide")),
        pytest.param(
            "build",
            marks=utils.skip_if_pyodide(
                "pyodide doesn't support multiple values for PIP_CONSTRAINT"
            ),
        ),
    ],
)
def test_overridden_pip_constraint(tmp_path, build_frontend):
    """
    Verify that users can use PIP_CONSTRAINT to specify a specific version of
    a build-system.requires dependency, by asserting the version of pytz in the
    setup.py.
    """
    project_dir = tmp_path / "project"

    project = test_projects.new_c_project(
        setup_py_add=textwrap.dedent(
            """
            import pytz
            assert pytz.__version__ == "2022.4", f"{pytz.__version__!r} != '2022.4'"
        """
        )
    )
    project.files["pyproject.toml"] = textwrap.dedent(
        """
        [build-system]
        requires = ["setuptools", "pytz"]
        build-backend = "setuptools.build_meta"
    """
    )
    project.generate(project_dir)

    if utils.get_platform() == "linux":
        # put the constraints file in the project directory, so it's available
        # in the docker container
        constraints_file = project_dir / "constraints.txt"
    else:
        constraints_file = tmp_path / "constraints.txt"

    constraints_file.write_text("pytz==2022.4")

    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_BUILD_FRONTEND": build_frontend,
            "PIP_CONSTRAINT": str(constraints_file),
            "CIBW_ENVIRONMENT_LINUX": "PIP_CONSTRAINT=./constraints.txt",
        },
        single_python=True,
    )

    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)
