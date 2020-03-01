from __future__ import print_function
import os
import sys
from unittest import TestCase

import spam


def normalize_path(path_str):
    """because of windows short path"""
    return os.path.normcase(path_str).replace("vssadm~1", "vssadministrator")


class TestSpam(TestCase):
    def test_system(self):
        self.assertEqual(0, spam.system('python -c "exit(0)"'))
        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))

    def test_virtualenv(self):
        virtualenv_path = normalize_path(os.environ.get("__CIBW_VIRTUALENV_PATH__"))
        if not virtualenv_path:
            self.fail("No virtualenv path defined in environment variable __CIBW_VIRTUALENV_PATH__")

        print("=[executable]", sys.executable)
        print("=[spam location]", spam.__file__)
        print("=[virtualenv path]", virtualenv_path)
        self.assertTrue(virtualenv_path in normalize_path(sys.executable))
        self.assertTrue(virtualenv_path in normalize_path(spam.__file__))
