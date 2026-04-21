import jinja2

from .base import TestProject
from .c import SPAM_C_TEMPLATE

PKG_A_PYPROJECT_TEMPLATE = r"""
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "spam"
version = "0.1.0"
"""

PKG_A_CMAKELISTS = r"""
cmake_minimum_required(VERSION 3.15...4.0)
project(spam C)

find_package(Python REQUIRED COMPONENTS Development.Module)

Python_add_library(spam MODULE WITH_SOABI spam.c)

install(TARGETS spam DESTINATION .)
"""

PKG_B_PYPROJECT_TEMPLATE = r"""
[build-system]
requires = ["meson-python"]
build-backend = "mesonpy"

[project]
name = "eggs"
version = "0.1.0"

[tool.cibuildwheel.windows]
config-settings = { "setup-args" = "--vsenv" }
archs = ["auto64"]
"""

PKG_B_MESON_BUILD = r"""
project('eggs', 'c',
  version: '0.1.0',
  default_options: ['warning_level=2'],
)

py = import('python').find_installation(pure: false)

py.extension_module('spam',
  'spam.c',
  install: true,
)
"""

TOPLEVEL_PYPROJECT = r"""
[tool.uv.workspace]
members = ["pkg_a", "pkg_b"]

[tool.cibuildwheel]
build-frontend = { name = "pip", args = ["--all-packages"] }
"""


def new_uv_workspace_project() -> TestProject:
    """Create a TestProject representing a uv workspace with two members.

    - pkg_a: a minimal package built with `scikit-build-core` (produces "spam" wheel).
    - pkg_b: a package using `meson-python` as its build backend (produces "eggs" wheel).
    The top-level project declares the uv workspace.
    """
    project = TestProject()

    # pkg_a: scikit-build-core project with a C extension
    project.files["pkg_a/pyproject.toml"] = jinja2.Template(PKG_A_PYPROJECT_TEMPLATE)
    project.files["pkg_a/spam.c"] = jinja2.Template(SPAM_C_TEMPLATE).render(
        spam_c_top_level_add="", spam_c_function_add=""
    )
    project.files["pkg_a/CMakeLists.txt"] = jinja2.Template(PKG_A_CMAKELISTS)

    # pkg_b: uses meson-python
    project.files["pkg_b/pyproject.toml"] = jinja2.Template(PKG_B_PYPROJECT_TEMPLATE)
    project.files["pkg_b/spam.c"] = jinja2.Template(SPAM_C_TEMPLATE).render(
        spam_c_top_level_add="", spam_c_function_add=""
    )
    project.files["pkg_b/meson.build"] = jinja2.Template(PKG_B_MESON_BUILD)

    # top-level workspace pyproject declares uv workspace
    project.files["pyproject.toml"] = jinja2.Template(TOPLEVEL_PYPROJECT)

    return project
