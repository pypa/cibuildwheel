
import os
import sys

from setuptools import setup, Extension



libraries = []
# Emscripten fails if you pass -lc...
# See: https://github.com/emscripten-core/emscripten/issues/16680
if sys.platform.startswith('linux') and "emscripten" not in os.environ.get("_PYTHON_HOST_PLATFORM", ""):
    libraries.extend(['m', 'c'])


setup(
    ext_modules=[Extension(
        'spam',
        sources=['spam.c'],
        libraries=libraries,
        
    )],
    
)