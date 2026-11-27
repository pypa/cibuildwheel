from __future__ import annotations

import jinja2

from .base import TestProject

CUSTOM_BACKEND_PY_TEMPLATE = r"""
import sys
import sysconfig
import zipfile
from pathlib import Path


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    {{ build_wheel_add | indent(4) }}
    py_tag = f"cp{sys.version_info[0]}{sys.version_info[1]}"
    plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    whl_name = f"demo_pkg-0.1.0-{py_tag}-{py_tag}-{plat}.whl"
    with zipfile.ZipFile(Path(wheel_directory) / whl_name, "w") as wheel:
        wheel.writestr(
            "demo_pkg-0.1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: demo-pkg\nVersion: 0.1.0\n",
        )
        wheel.writestr(
            "demo_pkg-0.1.0.dist-info/WHEEL",
            f"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: {py_tag}-{py_tag}-{plat}\n",
        )
    return whl_name
"""

PYPROJECT_TOML_TEMPLATE = r"""
[build-system]
requires = []
build-backend = "custom_backend"
backend-path = ["."]
"""


def new_custom_backend_project(*, build_wheel_add: str = "") -> TestProject:
    """Create a stub wheel for testing build hooks, not installation or repair."""
    project = TestProject()

    project.files.update(
        {
            "custom_backend.py": jinja2.Template(CUSTOM_BACKEND_PY_TEMPLATE.lstrip("\n")),
            "pyproject.toml": jinja2.Template(PYPROJECT_TOML_TEMPLATE.lstrip("\n")),
        }
    )

    project.template_context.update({"build_wheel_add": build_wheel_add})

    return project
