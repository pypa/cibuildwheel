import os

from setuptools import setup, Extension


setup(
    ext_modules=[Extension('spam.spam', sources=['spam/spam.c'])],
)
