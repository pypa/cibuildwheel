import subprocess

import pytest

from . import utils
from .test_projects.c import new_c_project


@utils.skip_if_pyodide(
    reason="pyodide build -h doesn't print help text https://github.com/pyodide/pyodide/issues/4783"
)
@pytest.mark.parametrize("frontend_name", ["pip", "build"])
def test_build_frontend_args(tmp_path, capfd, frontend_name):
    project = new_c_project()
    project_dir = tmp_path / "project"
    project.generate(project_dir)

    # the build will fail because the frontend is called with '-h' - it prints the help message
    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={"CIBW_BUILD_FRONTEND": f"{frontend_name}; args: -h"},
            single_python=True,
        )

    captured = capfd.readouterr()
    print(captured.out)

    # check that the help message was printed
    if frontend_name == "pip":
        assert "Usage:" in captured.out
        assert "Wheel Options:" in captured.out
    else:
        assert "usage:" in captured.out
        assert "A simple, correct Python build frontend." in captured.out
