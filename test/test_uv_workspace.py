import shutil
from pathlib import Path

import pytest

from . import test_projects, utils


def test_uv_workspace_pkg_a_scikit_build(
    tmp_path: Path, build_frontend_env: dict[str, str]
) -> None:
    """Test building pkg_a from a uv workspace - uses scikit-build-core."""
    if shutil.which("cmake") is None:
        pytest.skip("cmake not available (required for scikit-build-core)")

    project_dir = tmp_path / "project"

    # build a uv workspace project with the helper: pkg_a uses scikit-build-core
    project = test_projects.new_uv_workspace_project()
    project.generate(project_dir)

    # build pkg_a (spam) - it uses scikit-build-core with a C extension
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        package_dir="pkg_a",
        add_env=build_frontend_env,
        single_python=True,
    )

    # expected wheels: one from pkg_a (spam)
    expected_wheels = utils.expected_wheels("spam", "0.1.0", single_python=True)

    assert set(actual_wheels) == set(expected_wheels)


def test_uv_workspace_pkg_b_hatchling(tmp_path: Path, build_frontend_env: dict[str, str]) -> None:
    """Test building pkg_b from a uv workspace - uses hatchling."""
    project_dir = tmp_path / "project"

    # build a uv workspace project with the helper
    project = test_projects.new_uv_workspace_project()
    project.generate(project_dir)

    # build pkg_b (eggs) - it uses hatchling (pure Python)
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        package_dir="pkg_b",
        add_env=build_frontend_env,
        single_python=True,
    )

    # expected wheels: one from pkg_b (eggs)
    expected_wheels = utils.expected_wheels("eggs", "0.1.0", single_python=True)

    assert set(actual_wheels) == set(expected_wheels)
