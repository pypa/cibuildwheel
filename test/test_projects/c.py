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
    sts = strcmp(content, "spam") != 0;

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
