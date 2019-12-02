#include <Python.h>
#include <malloc.h>

#if !defined(__GLIBC_PREREQ)
#error "Must run on a glibc linux environment"
#endif

#if !__GLIBC_PREREQ(2, 5)  /* manylinux1 is glibc 2.5 */
#error "Must run on a glibc >= 2.5 linux environment"
#endif

static PyObject *
spam_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts = 0;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;

#if defined(__GLIBC_PREREQ) && __GLIBC_PREREQ(2, 17)  /* manylinux2014 is glibc 2.17 */
    // secure_getenv is only available in manylinux2014, ensuring
    // that only a manylinux2014 wheel is produced
    sts = (int)secure_getenv("NON_EXISTING_ENV_VARIABLE");
#elif defined(__GLIBC_PREREQ) && __GLIBC_PREREQ(2, 10)  /* manylinux2010 is glibc 2.12 */
    // malloc_info is only available on manylinux2010+
    sts = malloc_info(0, stdout);
#endif
    if (sts == 0) {
        sts = system(command);
    }
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
