from __future__ import annotations

import json
import subprocess
import textwrap
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

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    output_dir = tmp_path / "wheelhouse"

    (project_dir / "custom_backend.py").write_text(
        textwrap.dedent("""\
            import base64
            import hashlib
            import json
            import sys
            import sysconfig
            import zipfile
            from pathlib import Path

            def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
                py_tag = f"cp{sys.version_info[0]}{sys.version_info[1]}"
                plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
                whl_name = f"demo_pkg-0.1.0-{py_tag}-{py_tag}-{plat}.whl"
                whl_path = Path(wheel_directory) / whl_name
                files = {
                    "demo_pkg/config_settings.json": json.dumps(
                        config_settings, sort_keys=True
                    ).encode("utf-8"),
                    "demo_pkg-0.1.0.dist-info/METADATA": (
                        b"Metadata-Version: 2.1\\nName: demo-pkg\\nVersion: 0.1.0\\n"
                    ),
                    "demo_pkg-0.1.0.dist-info/WHEEL": (
                        f"Wheel-Version: 1.0\\nGenerator: custom\\n"
                        f"Root-Is-Purelib: false\\nTag: {py_tag}-{py_tag}-{plat}\\n"
                    ).encode("utf-8"),
                }
                record_lines = []
                with zipfile.ZipFile(whl_path, "w") as zf:
                    for name, data in files.items():
                        zf.writestr(name, data)
                        digest = (
                            base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                            .rstrip(b"=")
                            .decode("ascii")
                        )
                        record_lines.append(f"{name},sha256={digest},{len(data)}\\n")
                    record_lines.append("demo_pkg-0.1.0.dist-info/RECORD,,\\n")
                    zf.writestr(
                        "demo_pkg-0.1.0.dist-info/RECORD",
                        "".join(record_lines).encode("utf-8"),
                    )
                return whl_name
        """),
        encoding="utf-8",
    )
    (project_dir / "pyproject.toml").write_text(
        textwrap.dedent("""\
            [build-system]
            requires = []
            build-backend = "custom_backend"
            backend-path = ["."]

            [project]
            name = "demo-pkg"
            version = "0.1.0"
        """),
        encoding="utf-8",
    )

    add_env = {
        **build_frontend_env,
        "CIBW_CONFIG_SETTINGS": "--with-c-extensions tag=one tag=two",
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
        assert captured == {"--with-c-extensions": "", "tag": ["one", "two"]}
