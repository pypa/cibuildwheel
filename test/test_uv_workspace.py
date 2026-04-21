import shutil
from pathlib import Path

import packaging.utils
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


def test_uv_workspace_pkg_b_meson_python(
    tmp_path: Path, build_frontend_env: dict[str, str]
) -> None:
    """Test building pkg_b from a uv workspace - uses meson-python."""
    if shutil.which("meson") is None:
        pytest.skip("meson not available (required for meson-python)")

    project_dir = tmp_path / "project"

    # build a uv workspace project with the helper
    project = test_projects.new_uv_workspace_project()
    project.generate(project_dir)

    # build pkg_b (eggs) - it uses meson-python with a C extension
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        package_dir="pkg_b",
        add_env=build_frontend_env,
        single_python=True,
    )

    # expected wheels: one from pkg_b (eggs)
    # meson-python doesn't support win32 on a 64-bit CI machine
    is_windows = utils.get_platform() == "windows"
    expected_wheels = utils.expected_wheels(
        "eggs", "0.1.0", single_python=True, single_arch=is_windows
    )

    actual_wheels_normalized = {
        packaging.utils.parse_wheel_filename(w) for w in actual_wheels
    }
    expected_wheels_normalized = {
        packaging.utils.parse_wheel_filename(w) for w in expected_wheels
    }
    assert actual_wheels_normalized == expected_wheels_normalized
