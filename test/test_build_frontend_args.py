from __future__ import annotations

import subprocess

import pytest

from . import test_projects, utils

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "frontend_name",
    [
        pytest.param("pip", marks=utils.skip_if_pyodide("No pip for pyodide")),
        pytest.param(
            "build",
            marks=utils.skip_if_pyodide("pyodide only supports the pyodide-build frontend"),
        ),
        pytest.param(
            "pyodide-build",
            marks=pytest.mark.skipif(
                utils.get_platform() != "pyodide",
                reason="pyodide-build frontend is only valid on pyodide",
            ),
        ),
    ],
)
def test_build_frontend_args(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], frontend_name: str
) -> None:
    project = test_projects.new_c_project()
    project_dir = tmp_path / "project"
    project.generate(project_dir)

    # the build will fail because the frontend is called with '-h' - it prints the help message
    add_env = {"CIBW_BUILD_FRONTEND": f"{frontend_name}; args: -h"}
    if utils.get_platform() == "pyodide":
        add_env["TERM"] = "dumb"  # disable color / style
        add_env["NO_COLOR"] = "1"
    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, add_env=add_env, single_python=True)

    captured = capfd.readouterr()
    print(captured.out)

    # check that the help message was printed
    if frontend_name == "pip":
        assert "Usage:" in captured.out
        assert "Wheel Options:" in captured.out
    elif utils.get_platform() == "pyodide":
        assert "Usage: pyodide build" in captured.out
    else:
        assert "usage:" in captured.out
        assert "A simple, correct Python build frontend." in captured.out
