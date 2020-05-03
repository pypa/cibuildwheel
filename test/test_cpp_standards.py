import os
import textwrap

import jinja2
import pytest

from . import utils
from .template_projects import TemplateProject

cpp_template_project = TemplateProject()

cpp_template_project.files['setup.py'] = jinja2.Template(r'''
from setuptools import Extension, setup

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.cpp'], language="c++", extra_compile_args={{ extra_compile_args }})],
    version="0.1.0",
)
''')

cpp_template_project.files['spam.cpp'] = jinja2.Template(r'''
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

#if PY_MAJOR_VERSION >= 3
    #define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
    #define MOD_DEF(m, name, doc, methods, module_state_size) \
        static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, module_state_size, methods, }; \
        m = PyModule_Create(&moduledef);
    #define MOD_RETURN(m) return m;
#else
    #define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
    #define MOD_DEF(m, name, doc, methods, module_state_size) \
        m = Py_InitModule3(name, methods, doc);
    #define MOD_RETURN(m) return;
#endif

static PyMethodDef module_methods[] = {
    {"system", (PyCFunction)spam_system, METH_VARARGS,
     "Execute a shell command."},
    {NULL}  /* Sentinel */
};

MOD_INIT(spam)
{
    PyObject* m;

    MOD_DEF(m,
            "spam",
            "Example module",
            module_methods,
            -1)

    MOD_RETURN(m)
}
''')


def test_cpp11(tmpdir):
    # This test checks that the C++11 standard is supported
    project_dir = str(tmpdir)

    project = cpp_template_project.copy()
    extra_compile_args = ['/std:c++11'] if utils.platform == 'windows' else ['-std=c++11']
    project.template_context['extra_compile_args'] = extra_compile_args
    project.template_context['spam_cpp_top_level_add'] = '#include <array>'
    project.generate(project_dir)

    # VC++ for Python 2.7 does not support modern standards
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w and 'pp27-pypy_73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp14(tmpdir):
    # This test checks that the C++14 standard is supported
    project_dir = str(tmpdir)

    project = cpp_template_project.copy()
    extra_compile_args = ['/std:c++14'] if utils.platform == 'windows' else ['-std=c++14']
    project.template_context['extra_compile_args'] = extra_compile_args
    project.template_context['spam_cpp_top_level_add'] = "int a = 100'000;"
    project.generate(project_dir)

    # VC++ for Python 2.7 does not support modern standards
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.4 and 3.5 are compiled with MSVC 10, which does not support C++14
    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32 cp35-win*'}

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w
                       and 'cp35-cp35m-win' not in w]

    assert set(actual_wheels) == set(expected_wheels)


def test_cpp17(tmpdir):
    # This test checks that the C++17 standard is supported
    project_dir = str(tmpdir)

    project = cpp_template_project.copy()
    if utils.platform == 'windows':
        project.template_context['extra_compile_args'] = ['/std:c++17', '/wd5033']
    else:
        project.template_context['extra_compile_args'] = ['-std=c++17', '-Wno-register']

    project.template_context['spam_cpp_top_level_add'] = textwrap.dedent('''
            #include <utility>
            auto a = std::pair(5.0, false);
    ''')
    project.generate(project_dir)

    # Python and PyPy 2.7 use the `register` keyword which is forbidden in the C++17 standard
    # The manylinux1 docker image does not have a compiler which supports C++11
    # Python 3.5 and PyPy 3.6 are compiled with MSVC 10, which does not support C++17
    if os.environ.get('APPVEYOR_BUILD_WORKER_IMAGE', '') == 'Visual Studio 2015':
        pytest.skip('Visual Studio 2015 does not support C++17')

    add_env = {'CIBW_SKIP': 'cp27-win* pp27-win32 cp35-win* pp36-win32'}

    if utils.platform == 'macos':
        add_env['MACOSX_DEPLOYMENT_TARGET'] = '10.13'

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', macosx_deployment_target='10.13')
                       if 'cp27-cp27m-win' not in w
                       and 'pp27-pypy_73-win32' not in w
                       and 'cp35-cp35m-win' not in w
                       and 'pp36-pypy36_pp73-win32' not in w]

    assert set(actual_wheels) == set(expected_wheels)
