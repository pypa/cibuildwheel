from __future__ import annotations

import platform
import shutil
import textwrap

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


@pytest.mark.parametrize("use_pyproject_toml", [True, False])
def test_pyodide_build(tmp_path, use_pyproject_toml):
    if platform.machine() == "arm64":
        pytest.skip("emsdk doesn't work correctly on arm64")

    if not shutil.which("python3.12"):
        pytest.skip("Python 3.12 not installed")

    if use_pyproject_toml:
        basic_project.files["pyproject.toml"] = textwrap.dedent(
            """
            [build-system]
            requires = ["setuptools"]
            build-backend = "setuptools.build_meta"
            """
        )

    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_args=["--platform", "pyodide"],
    )

    # check that the expected wheels are produced
    expected_wheels = [
        "spam-0.1.0-cp312-cp312-emscripten_3_1_52_wasm32.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
