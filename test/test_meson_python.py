import packaging.utils

from . import test_projects, utils

meson_project = test_projects.new_meson_project()


def test_meson_python_basic(tmp_path, build_frontend_env):
    """Test that cibuildwheel can build a project with meson-python backend."""
    project_dir = tmp_path / "project"
    is_windows = utils.get_platform() == "windows"

    meson_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            **build_frontend_env,
            "CIBW_CONFIG_SETTINGS_WINDOWS": 'setup-args="--vsenv"',
            # building win32 wheels on a 64-bit CI machine with meson-python
            # requires a few extra steps outside cibuildwheel. See
            # https://github.com/pypa/cibuildwheel/pull/2718
            "CIBW_ARCHS_WINDOWS": "auto64",
        },
        single_python=True,
    )

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels(
        "spam", "0.1.0", single_python=True, single_arch=is_windows
    )
    actual_wheels_normalized = {packaging.utils.parse_wheel_filename(w) for w in actual_wheels}
    expected_wheels_normalized = {packaging.utils.parse_wheel_filename(w) for w in expected_wheels}
    assert actual_wheels_normalized == expected_wheels_normalized
