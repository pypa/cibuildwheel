import os

import utils


def test(tmp_path):
    project_dir = os.path.dirname(__file__)
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.

    utils.cibuildwheel_run(project_dir, output_dir=tmp_path)
