import jinja2

from .base import TestProject
from .c import SPAM_C_TEMPLATE


PKG_A_PYPROJECT_TEMPLATE = r"""
[build-system]
requires = ["scikit-build-core"]
build-backend = "scikit_build_core.build"

[project]
name = "pkg_a"
version = "0.1.0"
"""

PKG_A_CMAKELISTS = r"""
cmake_minimum_required(VERSION 3.15...4.0)
project(pkg_a C)

add_library(spam MODULE spam.c)
set_target_properties(spam PROPERTIES PREFIX "" OUTPUT_NAME "spam")
if(WIN32)
    set_target_properties(spam PROPERTIES SUFFIX ".pyd")
endif()

install(TARGETS spam
                RUNTIME DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/${PROJECT_NAME}
                LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}/${PROJECT_NAME}
                ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}/${PROJECT_NAME})
"""

PKG_B_PYPROJECT_TEMPLATE = r"""
[build-system]
requires = ["uv_backend"]
build-backend = "uv_backend.build"

[project]
name = "eggs"
version = "0.1.0"
dependencies = ["pkg_a @ file://../pkg_a"]
"""

TOPLEVEL_PYPROJECT = r"""
[build-system]
requires = ["uv_backend"]
build-backend = "uv_backend.build"

[tool.uv.workspace]
members = ["pkg_a", "pkg_b"]
"""


def new_uv_workspace_project() -> TestProject:
    """Create a TestProject representing a uv workspace with two members.

    - pkg_a: a minimal package built with `scikit-build-core` (a "core" library).
    - pkg_b: a package using `uv_backend` as its build backend and depending on pkg_a.
    The top-level project also declares `uv_backend` in its build-system.
    """
    project = TestProject()

    # pkg_a: scikit-build-core project (simple Python package)
    project.files["pkg_a/pyproject.toml"] = jinja2.Template(PKG_A_PYPROJECT_TEMPLATE)
    project.files["pkg_a/pkg_a/__init__.py"] = "__version__ = '0.1.0'\n"

    # Add a tiny C extension built via scikit-build-core (CMake)
    project.files["pkg_a/CMakeLists.txt"] = jinja2.Template(PKG_A_CMAKELISTS)
    project.files["pkg_a/spam.c"] = jinja2.Template(SPAM_C_TEMPLATE).render(
        spam_c_top_level_add="",
        spam_c_function_add=""
    )

    # pkg_b: uses uv_backend and depends on pkg_a (path dependency)
    project.files["pkg_b/pyproject.toml"] = jinja2.Template(PKG_B_PYPROJECT_TEMPLATE)
    project.files["pkg_b/eggs/__init__.py"] = "__version__ = '0.1.0'\n"

    # top-level workspace pyproject declares uv workspace and uv_backend
    project.files["pyproject.toml"] = jinja2.Template(TOPLEVEL_PYPROJECT)

    return project
