import os

from setuptools import setup, Extension

if os.environ.get('CIBUILDWHEEL', '0') != '1':
    raise Exception('CIBUILDWHEEL environment variable is not set to 1')

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
