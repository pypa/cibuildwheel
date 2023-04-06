from __future__ import annotations

import os
import subprocess
import textwrap

import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


def skip_if_no_msvc(arm64=False):
    programfiles = os.getenv("PROGRAMFILES(X86)", "") or os.getenv("PROGRAMFILES", "")
    if not programfiles:
        pytest.skip("Requires %PROGRAMFILES(X86)% variable to be set")

    vswhere = os.path.join(programfiles, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.isfile(vswhere):
        pytest.skip("Requires Visual Studio installation")

    require = "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"
    if arm64:
        require = "Microsoft.VisualStudio.Component.VC.Tools.ARM64"

    if not subprocess.check_output(
        [
            vswhere,
            "-latest",
            "-prerelease",
            "-property",
            "installationPath",
            "-requires",
            require,
        ]
    ):
        pytest.skip("Requires ARM64 compiler to be installed")


@pytest.mark.parametrize("use_pyproject_toml", [True, False])
def test_wheel_tag_is_correct_when_using_windows_cross_compile(tmp_path, use_pyproject_toml):
    if utils.platform != "windows":
        pytest.skip("This test is only relevant to Windows")

    skip_if_no_msvc(arm64=True)

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
        add_env={
            "CIBW_BUILD": "cp310-*",
        },
        add_args=["--archs", "ARM64"],
    )

    # check that the expected wheels are produced
    expected_wheels = [
        "spam-0.1.0-cp310-cp310-win_arm64.whl",
    ]

    print("actual_wheels", actual_wheels)
    print("expected_wheels", expected_wheels)

    assert set(actual_wheels) == set(expected_wheels)
