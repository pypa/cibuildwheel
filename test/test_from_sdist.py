import os
import subprocess
import sys
import textwrap
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

from test.test_projects.base import TestProject

from . import test_projects, utils

# utilities


def make_sdist(project: TestProject, working_dir: Path) -> Path:
    project_dir = working_dir / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    project.generate(project_dir)

    sdist_dir = working_dir / "sdist"
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(sdist_dir), str(project_dir)],
        check=True,
    )

    return next(sdist_dir.glob("*.tar.gz"))


def cibuildwheel_from_sdist_run(
    sdist_path: Path | str,
    add_env: Mapping[str, str] | None = None,
    config_file: str | None = None,
) -> list[str]:
    env = os.environ.copy()

    if add_env:
        env.update(add_env)

    env["CIBW_BUILD"] = "cp{}{}-*".format(*utils.SINGLE_PYTHON_VERSION)

    with TemporaryDirectory() as tmp_output_dir:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "cibuildwheel",
                *(["--config-file", config_file] if config_file else []),
                "--output-dir",
                str(tmp_output_dir),
                str(sdist_path),
            ],
            env=env,
            check=True,
        )
        return [p.name for p in Path(tmp_output_dir).iterdir()]


# tests


def test_simple(tmp_path):
    basic_project = test_projects.new_c_project()

    # make an sdist of the project
    sdist_dir = tmp_path / "sdist"
    sdist_dir.mkdir()
    sdist_path = make_sdist(basic_project, sdist_dir)

    setup_py_assertion_snippet = textwrap.dedent(
        """
        import os

        assert os.path.exists('setup.py')
        assert os.path.exists('{package}/setup.py')
        """,
    )
    setup_py_assertion_cmd = f'python -c "{setup_py_assertion_snippet!s}"'

    # build the wheels from sdist
    actual_wheels = cibuildwheel_from_sdist_run(
        sdist_path, add_env={"CIBW_BEFORE_BUILD": setup_py_assertion_cmd}
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)


def test_external_config_file_argument(tmp_path, capfd):
    basic_project = test_projects.new_c_project()

    # make an sdist of the project
    sdist_dir = tmp_path / "sdist"
    sdist_dir.mkdir()
    sdist_path = make_sdist(basic_project, sdist_dir)

    # add a config file
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [tool.cibuildwheel]
            before-all = 'echo "test log statement from before-all"'
            """
        )
    )

    # build the wheels from sdist
    actual_wheels = cibuildwheel_from_sdist_run(sdist_path, config_file=str(config_file))

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)

    # check that before-all was run
    captured = capfd.readouterr()
    assert "test log statement from before-all" in captured.out


def test_config_in_pyproject_toml(tmp_path, capfd):
    # make a project with a pyproject.toml
    project = test_projects.new_c_project()
    project.files["pyproject.toml"] = textwrap.dedent(
        """
        [tool.cibuildwheel]
        before-build = 'echo "test log statement from before-build 8419"'
        """
    )

    # make an sdist of the project
    sdist_dir = tmp_path / "sdist"
    sdist_dir.mkdir()
    sdist_path = make_sdist(project, sdist_dir)

    # build the wheels from sdist
    actual_wheels = cibuildwheel_from_sdist_run(sdist_path)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)

    # check that before-build was run
    captured = capfd.readouterr()
    assert "test log statement from before-build 8419" in captured.out


def test_internal_config_file_argument(tmp_path, capfd):
    # make a project with a config file inside
    project = test_projects.new_c_project(
        setup_cfg_add="include_package_data = True",
    )
    project.files["wheel_build_config.toml"] = textwrap.dedent(
        """
        [tool.cibuildwheel]
        before-all = 'echo "test log statement from before-all 1829"'
        """
    )
    project.files["MANIFEST.in"] = textwrap.dedent(
        """
        include wheel_build_config.toml
        """
    )

    # make an sdist of the project
    sdist_dir = tmp_path / "sdist"
    sdist_dir.mkdir()
    sdist_path = make_sdist(project, sdist_dir)

    # build the wheels from sdist, referencing the config file inside
    actual_wheels = cibuildwheel_from_sdist_run(
        sdist_path, config_file="{package}/wheel_build_config.toml"
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)
    assert set(actual_wheels) == set(expected_wheels)

    # check that before-all was run
    captured = capfd.readouterr()
    assert "test log statement from before-all 1829" in captured.out
