import os
import sys

from setuptools import (
    Extension,
    setup,
)

# check that we're running in the correct docker image as specified in the
# environment options CIBW_MANYLINUX1_*_IMAGE
if 'linux' in sys.platform and not os.path.exists('/dockcross'):
    raise Exception('/dockcross directory not found. Is this test running in the correct docker image?')

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
