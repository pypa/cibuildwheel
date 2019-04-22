import subprocess, sys, os
from glob import glob
import utils

def test():
    project_dir = os.path.dirname(__file__)
    
    # set up the environment
    env = os.environ.copy()
    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup.py
    env['CIBW_ENVIRONMENT'] = 'CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo \'test string 3\')" PATH=$PATH:/opt/cibw_test_path'
    env['CIBW_ENVIRONMENT_WINDOWS'] = 'CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo \'test string 3\')" PATH="$PATH;/opt/cibw_test_path"'

    # build the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir], env=env)
    
    # check that we got the right number of built wheels
    expected_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    built_wheels = glob('wheelhouse/*.whl')
    assert len(built_wheels) == len(expected_identifiers)
