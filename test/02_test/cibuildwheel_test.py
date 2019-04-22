import subprocess, sys, os
from glob import glob
import utils

def test():
    project_dir = os.path.dirname(__file__)
    # set up the environment
    env = os.environ.copy()
    env['CIBW_TEST_REQUIRES'] = 'nose'
    # the 'false ||' bit is to ensure this command runs in a shell on
    # mac/linux.
    env['CIBW_TEST_COMMAND'] = 'false || nosetests {project}/test'
    env['CIBW_TEST_COMMAND_WINDOWS'] = 'nosetests {project}/test'

    # build & test the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir], env=env)
    
    # also check that we got the right number of built wheels
    expected_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    built_wheels = glob('wheelhouse/*.whl')
    assert len(built_wheels) == len(expected_identifiers)
