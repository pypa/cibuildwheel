import jinja2
from .setuptools import SetuptoolsTemplateProject


spam_c_template = r'''
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


class CTemplateProject(SetuptoolsTemplateProject):
    def __init__(self, *, spam_c_top_level_add='', spam_c_function_add='', setup_py_add='',
                 setup_py_setup_args_add='', setup_cfg_add=''):
        setup_py_setup_args_add += '''
            ext_modules=[Extension('spam', sources=['spam.c'])],
        '''

        super().__init__(
            setup_py_add=setup_py_add,
            setup_py_setup_args_add=setup_py_setup_args_add,
            setup_cfg_add=setup_cfg_add
        )

        self.files.update({
            'spam.c': jinja2.Template(spam_c_template),
        })

        self.template_context.update({
            'spam_c_top_level_add': spam_c_top_level_add,
            'spam_c_function_add': spam_c_function_add,
        })
