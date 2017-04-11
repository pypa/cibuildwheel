from setuptools import setup, Extension
import sys

if sys.argv[-1] != '--name':
    # explode if run on Python 2.6 or Python 3.3 (these should be skipped)
    if sys.version_info[0:2] == (2, 6):
        raise Exception('Python 2.6 should be skipped')
    if sys.version_info[0:2] == (3, 3):
        raise Exception('Python 3.3 should be skipped')

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
