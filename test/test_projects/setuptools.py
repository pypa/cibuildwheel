import jinja2

from .base import TestProject
from .c import SPAM_C_TEMPLATE

_SPAM_C_WITH_MISSING_DLL = """\
#include <Python.h>

__declspec(dllimport) int cibwtest_add(int a, int b);

static PyObject *spam_filter(PyObject *self, PyObject *args)
{
    const char *content;
    int sts;
    if (!PyArg_ParseTuple(args, "s", &content))
        return NULL;
    sts = strcmp(content, "spam") != 0;
    cibwtest_add(0, 0);
    return PyLong_FromLong(sts);
}

static PyMethodDef module_methods[] = {
    {"filter", (PyCFunction)spam_filter, METH_VARARGS, "Execute a shell command."},
    {NULL}
};

PyMODINIT_FUNC PyInit_spam(void)
{
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT, "spam", "Example module", -1, module_methods,
    };
    return PyModule_Create(&moduledef);
}
"""

_SETUP_PY_WITH_MISSING_DLL = """\
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _orig_build_ext

here = Path(__file__).parent
dll_dir = here / "_cibwtest_dll"

class build_ext(_orig_build_ext):
    def build_extensions(self):
        if not self.compiler.initialized:
            self.compiler.initialize()
        dll_dir.mkdir(exist_ok=True)
        (dll_dir / "cibwtest.c").write_text(
            "__declspec(dllexport) int cibwtest_add(int a, int b) { return a + b; }\\n"
        )
        objs = self.compiler.compile(
            [str(dll_dir / "cibwtest.c")], output_dir=str(dll_dir)
        )
        self.compiler.link_shared_lib(
            objs,
            "cibwtest",
            output_dir=str(dll_dir),
            extra_postargs=[f"/IMPLIB:{dll_dir / 'cibwtest.lib'}"],
        )
        super().build_extensions()

setup(
    ext_modules=[Extension(
        "spam",
        sources=["spam.c"],
        libraries=["cibwtest"],
        library_dirs=[str(dll_dir)],
    )],
    cmdclass={"build_ext": build_ext},
)
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


def new_c_project_with_missing_dll() -> TestProject:
    """
    A Windows-only test project whose extension links against cibwtest.dll, a DLL
    built into a subdirectory that is not on PATH.  delvewheel will find the import
    in the PE table but cannot locate the file, so repair fails by default.
    Setting repair-wheel-command to "" disables repair and lets the build succeed.
    """
    project = TestProject()
    project.files.update(
        {
            "spam.c": _SPAM_C_WITH_MISSING_DLL,
            "setup.py": _SETUP_PY_WITH_MISSING_DLL,
            "setup.cfg": jinja2.Template(SETUP_CFG_TEMPLATE),
        }
    )
    return project


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
