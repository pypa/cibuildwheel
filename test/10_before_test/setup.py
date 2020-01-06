from setuptools import setup, Extension
import sys, os

# assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_BUILD step
# is the same one as is currently running.
version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
if os.path.exists(version_file):
    os.remove(version_file)

# check that the executable also was written
executable_file = 'c:\\pythonexecutable.txt' if sys.platform == 'win32' else '/tmp/pythonexecutable.txt'
if os.path.exists(executable_file):
    os.remove(executable_file)

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
