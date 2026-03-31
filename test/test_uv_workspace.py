import shutil

import packaging.utils

import pytest

from . import test_projects, utils


def test_uv_workspace_with_scikit_build_core(tmp_path, build_frontend_env):
    """Create a uv workspace with two subpackages; one uses scikit-build-core."""
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    if shutil.which("cmake") is None:
        pytest.skip("cmake not available (required for scikit-build-core)")

    project_dir = tmp_path / "project"

    # build a uv workspace project with the helper: pkg_a uses scikit-build-core
    project = test_projects.new_uv_workspace_project()
    project.generate(project_dir)

    # build the wheels from the workspace
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env=build_frontend_env,
        single_python=True,
    )

    # expected wheels: one from pkg_a (spam) and one from pkg_b (eggs)
    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", single_python=True
    ) + utils.expected_wheels("eggs", "0.1.0", single_python=True)

    assert set(actual_wheels) == set(expected_wheels)
