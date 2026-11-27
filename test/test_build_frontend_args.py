from __future__ import annotations

import json
import subprocess
import zipfile

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
    if frontend_name == "pyodide-build":
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
    elif frontend_name == "pyodide-build":
        assert "Usage: pyodide build" in captured.out
    else:
        assert "usage:" in captured.out
        assert "A simple, correct Python build frontend." in captured.out


def test_config_settings(tmp_path: Path, build_frontend_env: dict[str, str]) -> None:
    if build_frontend_env["CIBW_BUILD_FRONTEND"] == "pyodide-build":
        pytest.skip("pyodide-build requires pyodide platform")

    project = test_projects.new_custom_backend_project()
    project_dir = tmp_path / "project"
    project.generate(project_dir)
    output_dir = tmp_path / "wheelhouse"

    add_env = {
        **build_frontend_env,
        "CIBW_CONFIG_SETTINGS": (
            "--with-c-extensions "
            "tag=one tag=two "
            'spaced="hello world" '
            """dquote='say "hi"' """
            """squote="it's ok" """
            "eq=x=y=z "
            "empty= "
            "--opt=-val"
        ),
        "CIBW_REPAIR_WHEEL_COMMAND": "",
        "CIBW_SKIP": "*-musllinux_*",
    }
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        output_dir=output_dir,
        add_env=add_env,
        single_python=True,
    )
    assert actual_wheels

    for wheel_name in actual_wheels:
        with zipfile.ZipFile(output_dir / wheel_name) as zf:
            captured = json.loads(zf.read("demo_pkg/config_settings.json").decode("utf-8"))
        assert captured == {
            "--with-c-extensions": "",
            "tag": ["one", "two"],
            "spaced": "hello world",
            "dquote": 'say "hi"',
            "squote": "it's ok",
            "eq": "x=y=z",
            "empty": "",
            "--opt": "-val",
        }
