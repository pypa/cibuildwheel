import subprocess, sys, os
from glob import glob
import utils

def test():
    project_dir = os.path.dirname(__file__)
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.

    # build the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir])
    
    # check that we got the right number of built wheels
    expected_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    built_wheels = glob('wheelhouse/*.whl')
    assert len(built_wheels) == len(expected_identifiers)
