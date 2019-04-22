import subprocess, sys, os
from glob import glob
project_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(os.path.dirname(project_dir), 'shared'))

import utils

def test():
    # build the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir]) 
    
    # check that every wheel is produced
    if utils.platform == 'linux':
        assert glob('wheelhouse/*-cp27-cp27m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp27-cp27mu-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp34-cp34m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp35-cp35m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp36-cp36m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp37-cp37m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp27-cp27m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp27-cp27mu-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp34-cp34m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp35-cp35m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp36-cp36m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp37-cp37m-manylinux1_i686.whl')

    if utils.platform == 'windows':
        assert glob('wheelhouse/*-cp27-*-win32.whl')
        assert glob('wheelhouse/*-cp34-*-win32.whl')
        assert glob('wheelhouse/*-cp35-*-win32.whl')
        assert glob('wheelhouse/*-cp36-*-win32.whl')
        assert glob('wheelhouse/*-cp37-*-win32.whl')
        assert glob('wheelhouse/*-cp27-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp34-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp35-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp36-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp37-*-win_amd64.whl')

    if utils.platform == 'macos':
        assert glob('wheelhouse/*-cp27-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp34-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp35-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp36-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp37-*-macosx_10_6_intel.whl')

    # also check that the number of built wheels matches the number of build
    # identifiers
    expected_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    built_wheels = glob('wheelhouse/*.whl')
    assert len(built_wheels) == len(expected_identifiers)
