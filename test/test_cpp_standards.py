import os

import jinja2
import pytest

from . import utils
from .test_projects import TestProject

cpp_test_project = TestProject()

setup_py_template = r"""
from setuptools import Extension, setup

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.cpp'], language="c++", extra_compile_args={{ extra_compile_args }})],
    version="0.1.0",
)
"""

spam_cpp_template = r"""
#include <Python.h>

{{ spam_cpp_top_level_add }}

static PyObject *
spam_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;
    sts = system(command);
    return PyLong_FromLong(sts);
}

/* Module initialization */
static PyMethodDef module_methods[] = {
    {"system", (PyCFunction)spam_system, METH_VARARGS,
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

cpp_test_project.files["setup.py"] = jinja2.Template(setup_py_template)
cpp_test_project.files["spam.cpp"] = jinja2.Template(spam_cpp_template)

cpp11_project = cpp_test_project.copy()
cpp11_project.template_context["extra_compile_args"] = (
    ["/std:c++11"] if utils.platform == "windows" else ["-std=c++11"]
)
cpp11_project.template_context["spam_cpp_top_level_add"] = "#include <array>"


def test_cpp11(tmp_path):
    # This test checks that the C++11 standard is supported
    project_dir = tmp_path / "project"

    cpp11_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir)
    expected_wheels = [w for w in utils.expected_wheels("spam", "0.1.0")]

    assert set(actual_wheels) == set(expected_wheels)


cpp14_project = cpp_test_project.copy()
cpp14_project.template_context["extra_compile_args"] = (
    ["/std:c++14"] if utils.platform == "windows" else ["-std=c++14"]
)
cpp14_project.template_context["spam_cpp_top_level_add"] = "int a = 100'000;"


def test_cpp14(tmp_path):
    # This test checks that the C++14 standard is supported
    project_dir = tmp_path / "project"

    cpp14_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir)
    expected_wheels = [w for w in utils.expected_wheels("spam", "0.1.0")]

    assert set(actual_wheels) == set(expected_wheels)


cpp17_project = cpp_test_project.copy()

cpp17_project.template_context["extra_compile_args"] = [
    "/std:c++17" if utils.platform == "windows" else "-std=c++17"
]
cpp17_project.template_context[
    "spam_cpp_top_level_add"
] = r"""
#include <utility>
auto a = std::pair(5.0, false);
"""


def test_cpp17(tmp_path):
    # This test checks that the C++17 standard is supported
    project_dir = tmp_path / "project"

    cpp17_project.generate(project_dir)

    if os.environ.get("APPVEYOR_BUILD_WORKER_IMAGE", "") == "Visual Studio 2015":
        pytest.skip("Visual Studio 2015 does not support C++17")

    # Pypy's distutils sets the default compiler to 'msvc9compiler', which
    # is too old to support cpp17.
    add_env = {"CIBW_SKIP": "pp??-*"}

    if utils.platform == "macos":
        add_env["MACOSX_DEPLOYMENT_TARGET"] = "10.13"

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [
        w
        for w in utils.expected_wheels("spam", "0.1.0", macosx_deployment_target="10.13")
        if "-pp" not in w
    ]

    assert set(actual_wheels) == set(expected_wheels)
