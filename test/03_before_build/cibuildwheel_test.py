import subprocess, sys, os
from glob import glob
project_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(project_dir), 'shared'))

import utils

def test():
    # set up the environment
    env = os.environ.copy()
    # write python version information to a temporary file, this is checked
    # in setup.py
    env['CIBW_BEFORE_BUILD'] = "python -c \"import sys; open('/tmp/pythonversion.txt', 'w').write(sys.version)\" && python -c \"import sys; open('/tmp/pythonexecutable.txt', 'w').write(sys.executable)\""
    env['CIBW_BEFORE_BUILD_WINDOWS'] = "python -c \"import sys; open('c:\\pythonversion.txt', 'w').write(sys.version)\" && python -c \"import sys; open('c:\\pythonexecutable.txt', 'w').write(sys.executable)\""

    # build the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir], env=env)
    
    # check that we got the right number of built wheels
    expected_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    built_wheels = glob('wheelhouse/*.whl')
    assert len(built_wheels) == len(expected_identifiers)
