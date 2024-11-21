from __future__ import annotations

import shutil
import sys
import textwrap

import pytest

from cibuildwheel.util import CIBW_CACHE_PATH, CIProvider, detect_ci_provider

from . import test_projects, utils

basic_project = test_projects.new_c_project()
basic_project.files["check_node.py"] = r"""
import sys
import shutil
from pathlib import Path
from pyodide.code import run_js


def check_node():
    # cibuildwheel adds a pinned node version to the PATH
    # check it's in the PATH then, check it's the one that runs Pyodide
    cibw_cache_path = Path(sys.argv[1]).resolve(strict=True)
    # find the node executable in PATH
    node = shutil.which("node")
    assert node is not None, "node is None"
    node_path = Path(node).resolve(strict=True)
    # it shall be in cibuildwheel cache
    assert cibw_cache_path in node_path.parents, f"{cibw_cache_path} not a parent of {node_path}"
    # find the path to the node executable that runs pyodide
    node_js = run_js("globalThis.process.execPath")
    assert node_js is not None, "node_js is None"
    node_js_path = Path(node_js).resolve(strict=True)
    # it shall be the one pinned by cibuildwheel
    assert node_js_path == node_path, f"{node_js_path} != {node_path}"


if __name__ == "__main__":
    check_node()
"""


@pytest.mark.parametrize("use_pyproject_toml", [True, False])
def test_pyodide_build(tmp_path, use_pyproject_toml):
    if sys.platform == "win32":
        pytest.skip("emsdk doesn't work correctly on Windows")

    if not shutil.which("python3.12"):
        pytest.skip("Python 3.12 not installed")

    if detect_ci_provider() == CIProvider.travis_ci:
        pytest.skip("Python 3.12 is just a non-working pyenv shim")

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

    # check for node in 1 case only to reduce CI load
    add_env = {}
    if use_pyproject_toml:
        add_env["CIBW_TEST_COMMAND"] = f"python {{project}}/check_node.py {CIBW_CACHE_PATH}"

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_args=["--platform", "pyodide"],
        add_env=add_env,
    )

    # check that the expected wheels are produced
    expected_wheels = [
        "spam-0.1.0-cp312-cp312-pyodide_2024_0_wasm32.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
