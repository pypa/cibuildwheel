import jinja2

from .base import TestProject

SPAM_C_TEMPLATE = r"""
#include <Python.h>

{{ spam_c_top_level_add }}

static PyObject *
spam_filter(PyObject *self, PyObject *args)
{
    const char *content;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &content))
        return NULL;

    // Spam should not be allowed through the filter.
    sts = strcmp(content, "spam");

    {{ spam_c_function_add | indent(4) }}

    return PyLong_FromLong(sts);
}

/* Module initialization */
static PyMethodDef module_methods[] = {
    {"filter", (PyCFunction)spam_filter, METH_VARARGS,
     "Execute a shell command."},
    {NULL}  /* Sentinel */
};

PyMODINIT_FUNC PyInit_spam(void)
{
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT, "spam", "Example module", -1, module_methods,
    };
    return PyModule_Create(&moduledef);
}
"""

SETUP_PY_TEMPLATE = r"""
import os
import sys

from setuptools import setup, Extension

{{ setup_py_add }}

libraries = []
# Emscripten fails if you pass -lc...
# See: https://github.com/emscripten-core/emscripten/issues/16680
if sys.platform.startswith('linux') and "emscripten" not in os.environ.get("_PYTHON_HOST_PLATFORM", ""):
    libraries.extend(['m', 'c'])


setup(
    ext_modules=[Extension(
        'spam',
        sources=['spam.c'],
        libraries=libraries,
        {{ setup_py_extension_args_add | indent(8) }}
    )],
    {{ setup_py_setup_args_add | indent(4) }}
)
"""

SETUP_CFG_TEMPLATE = r"""
[metadata]
name = spam
version = 0.1.0

{{ setup_cfg_add }}
"""


def new_c_project(
    *,
    spam_c_top_level_add: str = "",
    spam_c_function_add: str = "",
    setup_py_add: str = "",
    setup_py_extension_args_add: str = "",
    setup_py_setup_args_add: str = "",
    setup_cfg_add: str = "",
) -> TestProject:
    project = TestProject()

    project.files.update(
        {
            "spam.c": jinja2.Template(SPAM_C_TEMPLATE),
            "setup.py": jinja2.Template(SETUP_PY_TEMPLATE),
            "setup.cfg": jinja2.Template(SETUP_CFG_TEMPLATE),
        }
    )

    project.template_context.update(
        {
            "spam_c_top_level_add": spam_c_top_level_add,
            "spam_c_function_add": spam_c_function_add,
            "setup_py_add": setup_py_add,
            "setup_py_extension_args_add": setup_py_extension_args_add,
            "setup_py_setup_args_add": setup_py_setup_args_add,
            "setup_cfg_add": setup_cfg_add,
        }
    )

    return project
