from setuptools import setup, Extension
import sys

# here we assert that the Python version as written to version.txt in the CIBW_BEFORE_BUILD step
# is the same one as is currently running.
sys.stderr.write('sys.argv \n' + str(sys.argv))
if sys.argv[-1] != '--name':
    with open('version.txt') as f:
        stored_version = f.read()
    print('version is', stored_version)
    assert stored_version == sys.version

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
