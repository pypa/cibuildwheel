from __future__ import annotations
import platform

import textwrap

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


@pytest.mark.parametrize("use_pyproject_toml", [True, False])
def test_emscripten_build(tmp_path, use_pyproject_toml):
    if platform.machine() == "arm64":
        pytest.skip("emsdk doesn't work correctly on arm64")

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
        "spam-0.1.0-cp310-cp310-emscripten_3_1_27_wasm32.whl",
        "spam-0.1.0-cp311-cp311-emscripten_3_1_32_wasm32.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
