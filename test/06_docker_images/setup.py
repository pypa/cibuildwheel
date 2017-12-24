import os, sys

from setuptools import setup, Extension

if sys.argv[-1] != '--name':
    # check that we're running in the correct docker image as specified in the
    # environment options CIBW_MANYLINUX1_*_IMAGE
    if not os.path.exists('/dockcross'):
        raise Exception('/dockcross directory not found. Is this test running in the correct docker image?')

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
