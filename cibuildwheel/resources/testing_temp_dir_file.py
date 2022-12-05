# this file is copied to the testing cwd, to raise the below error message if
# pytest/unittest is run from there.

import unittest


class TestStringMethods(unittest.TestCase):
    def test_fail(self):
        self.fail(
            "cibuildwheel executes tests from a different working directory to "
            "your project. This ensures only your wheel is imported, preventing "
            "Python from accessing files that haven't been packaged into the "
            "wheel. Please specify a path to your tests when invoking pytest "
            "using the {project} placeholder, e.g. `pytest {project}` or "
            "`pytest {project}/tests`. cibuildwheel will replace {project} with "
            "the path to your project."
        )
