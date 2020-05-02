#include <Python.h>
#include <string>

// Depending on the requested standard, use a modern C++ feature
// that was introduced in that standard.
#if STANDARD == 11
    #include <array>
#elif STANDARD == 14
    int a = 100'000;
#elif STANDARD == 17
    #include <utility>
    auto a = std::pair(5.0, false);
#else
    #error Standard needed
#endif

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
