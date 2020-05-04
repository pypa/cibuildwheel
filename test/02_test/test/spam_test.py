from __future__ import print_function
import os
import platform
import sys
import struct
from unittest import TestCase

import spam


def path_contains(parent, child):
    ''' returns True if `child` is inside `parent`.

    Works around path-comparison bugs caused by short-paths on Windows e.g.
    vssadm~1 instead of vssadministrator
    '''
    parent = os.path.abspath(parent)
    child = os.path.abspath(child)

    while child != os.path.dirname(child):
        child = os.path.dirname(child)
        if os.stat(parent) == os.stat(child):
            # parent and child refer to the same directory on the filesystem
            return True
    return False


class TestSpam(TestCase):
    def test_system(self):
        self.assertEqual(0, spam.system('python -c "exit(0)"'))
        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))

    def test_virtualenv(self):
        virtualenv_path = os.environ.get("__CIBW_VIRTUALENV_PATH__")
        if not virtualenv_path:
            self.fail("No virtualenv path defined in environment variable __CIBW_VIRTUALENV_PATH__")

        print("=[executable]", sys.executable)
        print("=[spam location]", spam.__file__)
        print("=[virtualenv path]", virtualenv_path)
        print("=[listdir]", os.listdir(virtualenv_path))
        if os.path.exists(os.path.join(virtualenv_path, 'Scripts')):
            print("=[listdir]2", os.listdir(os.path.join(virtualenv_path, 'Scripts')))
        if os.path.exists(os.path.join(virtualenv_path, 'bin')):
            print("=[listdir]2", os.listdir(os.path.join(virtualenv_path, 'bin')))
        self.assertTrue(path_contains(virtualenv_path, sys.executable))
        self.assertTrue(path_contains(virtualenv_path, spam.__file__))

    def test_uname(self):
        if platform.system() == "Windows":
            return
        # if we're running in 32-bit Python, check that the machine is i686.
        # See #336 for more info.
        bits = struct.calcsize("P") * 8
        if bits == 32:
            self.assertEqual(platform.machine(), "i686")
