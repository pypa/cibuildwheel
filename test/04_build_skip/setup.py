import sys

from setuptools import (
    Extension,
    setup,
)

# explode if run on Python 2.7 or Python 3.4 (these should be skipped)
if sys.version_info[0:2] == (2, 7):
    raise Exception('Python 2.7 should not be built')
if sys.version_info[0:2] == (3, 4):
    raise Exception('Python 3.4 should be skipped')

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
