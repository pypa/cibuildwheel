from setuptools import (
    Extension,
    setup,
)

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    extras_require={'test': ['nose']},
    version="0.1.0",
)
