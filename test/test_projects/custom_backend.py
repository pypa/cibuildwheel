from __future__ import annotations

import jinja2

from .base import TestProject

CUSTOM_BACKEND_PY_TEMPLATE = r"""
import base64
import hashlib
import json
import sys
import sysconfig
import zipfile
from pathlib import Path


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    {{ build_wheel_add | indent(4) }}
    py_tag = f"cp{sys.version_info[0]}{sys.version_info[1]}"
    plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    whl_name = f"demo_pkg-0.1.0-{py_tag}-{py_tag}-{plat}.whl"
    whl_path = Path(wheel_directory) / whl_name
    files = {
        "demo_pkg/config_settings.json": json.dumps(
            config_settings, sort_keys=True
        ).encode("utf-8"),
        "demo_pkg-0.1.0.dist-info/METADATA": (
            b"Metadata-Version: 2.1\nName: demo-pkg\nVersion: 0.1.0\n"
        ),
        "demo_pkg-0.1.0.dist-info/WHEEL": (
            f"Wheel-Version: 1.0\nGenerator: custom\n"
            f"Root-Is-Purelib: false\nTag: {py_tag}-{py_tag}-{plat}\n"
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
            record_lines.append(f"{name},sha256={digest},{len(data)}\n")
        record_lines.append("demo_pkg-0.1.0.dist-info/RECORD,,\n")
        zf.writestr(
            "demo_pkg-0.1.0.dist-info/RECORD",
            "".join(record_lines).encode("utf-8"),
        )
    return whl_name
"""

PYPROJECT_TOML_TEMPLATE = r"""
[build-system]
requires = []
build-backend = "custom_backend"
backend-path = ["."]

[project]
name = "demo-pkg"
version = "0.1.0"
{{ pyproject_toml_add }}
"""


def new_custom_backend_project(
    *,
    build_wheel_add: str = "",
    pyproject_toml_add: str = "",
) -> TestProject:
    project = TestProject()

    project.files.update(
        {
            "custom_backend.py": jinja2.Template(CUSTOM_BACKEND_PY_TEMPLATE.lstrip("\n")),
            "pyproject.toml": jinja2.Template(PYPROJECT_TOML_TEMPLATE.lstrip("\n")),
        }
    )

    project.template_context.update(
        {
            "build_wheel_add": build_wheel_add,
            "pyproject_toml_add": pyproject_toml_add,
        }
    )

    return project
