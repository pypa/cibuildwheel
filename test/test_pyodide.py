import contextlib
import subprocess
import sys
import textwrap

import pytest

from cibuildwheel.util.file import CIBW_CACHE_PATH

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
        pytest.skip("pyodide-build doesn't work correctly on Windows")

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
    add_env = {"CIBW_ENABLE": "pyodide-prerelease"}
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
        "spam-0.1.0-cp313-cp313-pyodide_2025_0_wasm32.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)


def test_pyodide_version_incompatible(tmp_path, capfd):
    if sys.platform == "win32":
        pytest.skip("pyodide-build doesn't work correctly on Windows")

    basic_project.generate(tmp_path)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            tmp_path,
            add_args=["--platform", "pyodide"],
            add_env={
                "CIBW_DEPENDENCY_VERSIONS": "packages: pyodide-build==0.29.3",
                "CIBW_PYODIDE_VERSION": "0.26.0a6",
            },
        )

    out, err = capfd.readouterr()

    assert "is not compatible with the pyodide-build version" in err


@pytest.mark.parametrize("expect_failure", [True, False])
def test_pyodide_build_and_test(tmp_path, expect_failure):
    if sys.platform == "win32":
        pytest.skip("pyodide-build doesn't work correctly on Windows")

    if expect_failure:
        basic_project.files["test/spam_test.py"] = textwrap.dedent(r"""
            def test_filter():
                assert 0 == 1
        """)
    else:
        basic_project.files["test/spam_test.py"] = textwrap.dedent(r"""
            import spam
            def test_filter():
                assert spam.filter("spam") == 0
        """)
    basic_project.generate(tmp_path)

    context = (
        pytest.raises(subprocess.CalledProcessError) if expect_failure else contextlib.nullcontext()
    )
    with context:
        # build the wheels
        actual_wheels = utils.cibuildwheel_run(
            tmp_path,
            add_args=["--platform", "pyodide"],
            add_env={
                "CIBW_TEST_REQUIRES": "pytest",
                "CIBW_TEST_COMMAND": "python -m pytest {project}",
                "CIBW_ENABLE": "pyodide-prerelease",
            },
        )
        # check that the expected wheels are produced
        expected_wheels = [
            "spam-0.1.0-cp312-cp312-pyodide_2024_0_wasm32.whl",
            "spam-0.1.0-cp313-cp313-pyodide_2025_0_wasm32.whl",
        ]
        print("actual_wheels", actual_wheels)
        print("expected_wheels", expected_wheels)
        assert set(actual_wheels) == set(expected_wheels)
