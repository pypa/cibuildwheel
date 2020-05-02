from setuptools import (
    Extension,
    setup,
)

setup(
    ext_modules=[Extension('spam.spam', sources=['spam/spam.c'])],
)
