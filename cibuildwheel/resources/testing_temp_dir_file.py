# this file is copied to the testing cwd, to raise the below error message if
# pytest/unittest is run from there.

import sys
import unittest
from typing import NoReturn


class TestStringMethods(unittest.TestCase):
    def test_fail(self) -> NoReturn:
        if sys.platform == "ios":
            msg = (
                "You tried to run tests from the testbed app's working "
                "directory, without specifying `test-sources`. "
                "On iOS, you must copy your test files to the testbed app by "
                "setting the `test-sources` option in your cibuildwheel "
                "configuration."
            )
        else:
            msg = (
                "cibuildwheel executes tests from a different working directory to "
                "your project. This ensures only your wheel is imported, preventing "
                "Python from accessing files that haven't been packaged into the "
                "wheel. "
                "\n\n"
                "Please specify a path to your tests when invoking pytest "
                "using the {project} placeholder, e.g. `pytest {project}` or "
                "`pytest {project}/tests`. cibuildwheel will replace {project} with "
                "the path to your project. "
                "\n\n"
                "Alternatively, you can specify your test files using the "
                "`test-sources` option, and cibuildwheel will copy them to the "
                "working directory for testing."
            )

        self.fail(msg)
