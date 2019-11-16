from setuptools import setup, Extension

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    extras_require={'test': ['nose']},
    version="0.1.0",
)
