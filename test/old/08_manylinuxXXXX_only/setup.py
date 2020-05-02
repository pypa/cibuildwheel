from setuptools import (
    Extension,
    setup,
)

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
