import os


def test(utils):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.

    utils.cibuildwheel_run()
