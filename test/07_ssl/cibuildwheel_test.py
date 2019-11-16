import os
from utils import utils


PROJECT_DIR = os.path.dirname(__file__)


def test(utils):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.

    utils.cibuildwheel_run(PROJECT_DIR)
