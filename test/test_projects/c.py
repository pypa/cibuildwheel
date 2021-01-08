import jinja2

from .base import TestProject

SPAM_C_TEMPLATE = r'''
#include <Python.h>

{{ spam_c_top_level_add }}

static PyObject *
spam_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;

    sts = system(command);

    {{ spam_c_function_add | indent(4) }}

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
'''

SETUP_PY_TEMPLATE = r'''
from setuptools import setup, Extension

{{ setup_py_add }}

setup(
    ext_modules=[Extension('spam', sources=['spam.c'])],
    {{ setup_py_setup_args_add | indent(4) }}
)
'''

SETUP_CFG_TEMPLATE = r'''
[metadata]
name = spam
version = 0.1.0

{{ setup_cfg_add }}
'''


def new_c_project(*, spam_c_top_level_add='', spam_c_function_add='', setup_py_add='',
                  setup_py_setup_args_add='', setup_cfg_add=''):
    project = TestProject()

    project.files.update({
        'spam.c': jinja2.Template(SPAM_C_TEMPLATE),
        'setup.py': jinja2.Template(SETUP_PY_TEMPLATE),
        'setup.cfg': jinja2.Template(SETUP_CFG_TEMPLATE),
    })

    project.template_context.update({
        'spam_c_top_level_add': spam_c_top_level_add,
        'spam_c_function_add': spam_c_function_add,
        'setup_py_add': setup_py_add,
        'setup_py_setup_args_add': setup_py_setup_args_add,
        'setup_cfg_add': setup_cfg_add,
    })

    return project
