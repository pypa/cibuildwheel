import sys
import os
from unittest import TestCase


class TestBeforeTest(TestCase):
    def test_version(self):
        # assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_TEST step
        # is the same one as is currently running.
        # because of use symlinks in MacOS run this test is also need
        version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
        with open(version_file) as f:
            stored_version = f.read()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

    def test_executable(self):
        # check that the executable also was written
        executable_file = 'c:\\pythonexecutable.txt' if sys.platform == 'win32' else '/tmp/pythonexecutable.txt'
        with open(executable_file) as f:
            stored_executable = f.read()
        print('stored_executable', stored_executable)
        print('sys.executable', sys.executable)
        #  Works around path-comparison bugs caused by short-paths on Windows e.g.
        #  vssadm~1 instead of vssadministrator

        assert os.stat(stored_executable) == os.stat(sys.executable)
