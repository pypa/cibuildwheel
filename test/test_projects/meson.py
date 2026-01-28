import jinja2

from .base import TestProject
from .c import SPAM_C_TEMPLATE

PYPROJECT_TOML_TEMPLATE = r"""
[build-system]
requires = ["meson-python"]
build-backend = "mesonpy"

[project]
name = "spam"
version = "0.1.0"

[tool.cibuildwheel.windows]
archs = ["auto64"]
"""

MESON_BUILD_TEMPLATE = r"""
project('spam', 'c',
  version: '0.1.0',
  default_options: ['warning_level=2'],
)

py = import('python').find_installation(pure: false)

py.extension_module('spam',
  'spam.c',
  install: true,
)
"""


def new_meson_project(
    *,
    spam_c_top_level_add: str = "",
    spam_c_function_add: str = "",
) -> TestProject:
    project = TestProject()

    project.files.update(
        {
            "spam.c": jinja2.Template(SPAM_C_TEMPLATE),
            "pyproject.toml": jinja2.Template(PYPROJECT_TOML_TEMPLATE),
            "meson.build": jinja2.Template(MESON_BUILD_TEMPLATE),
        }
    )

    project.template_context.update(
        {
            "spam_c_top_level_add": spam_c_top_level_add,
            "spam_c_function_add": spam_c_function_add,
        }
    )

    return project
