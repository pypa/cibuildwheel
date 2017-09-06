from setuptools import setup, Extension
import sys, os

if sys.argv[-1] != '--name':
    # assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_BUILD step
    # is the same one as is currently running.
    version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
    with open(version_file) as f:
        stored_version = f.read()
    print('stored_version', stored_version)
    print('sys.version', sys.version)
    assert stored_version == sys.version

    # check that the executable also was written
    executable_file = 'c:\\pythonexecutable.txt' if sys.platform == 'win32' else '/tmp/pythonexecutable.txt'
    with open(executable_file) as f:
        stored_executable = f.read()
    print('stored_executable', stored_executable)
    print('sys.executable', sys.executable)
    assert os.path.samefile(stored_executable, sys.executable)

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
