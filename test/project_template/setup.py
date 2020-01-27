from setuptools import setup, Extension

{{setup_py_add}}

setup(
    name="spam",
    ext_modules=[Extension("spam", sources=["spam.c"])],
    version="0.1.0",
    {{setup_py_setup_args_add | indent(4)}}
)
