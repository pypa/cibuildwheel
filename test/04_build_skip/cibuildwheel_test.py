import subprocess, sys, os
from glob import glob
import utils

def test():
    project_dir = os.path.dirname(__file__)
    
    # set up the environment
    env = os.environ.copy()
    env.update({
        'CIBW_BUILD': 'cp3?-*',
        'CIBW_SKIP': 'cp34-*',
    })

    # build the wheels
    subprocess.check_call([sys.executable, '-m', 'cibuildwheel', project_dir], env=env)

    # check that we got the right wheels. There should be no 2.7 or 3.4.
    if utils.platform == 'linux':
        assert not glob('wheelhouse/*-cp27-cp27m-manylinux1_x86_64.whl')
        assert not glob('wheelhouse/*-cp27-cp27mu-manylinux1_x86_64.whl')
        assert not glob('wheelhouse/*-cp34-cp34m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp35-cp35m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp36-cp36m-manylinux1_x86_64.whl')
        assert glob('wheelhouse/*-cp37-cp37m-manylinux1_x86_64.whl')
        assert not glob('wheelhouse/*-cp27-cp27m-manylinux1_i686.whl')
        assert not glob('wheelhouse/*-cp27-cp27mu-manylinux1_i686.whl')
        assert not glob('wheelhouse/*-cp34-cp34m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp35-cp35m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp36-cp36m-manylinux1_i686.whl')
        assert glob('wheelhouse/*-cp37-cp37m-manylinux1_i686.whl')

    if utils.platform == 'windows':
        assert not glob('wheelhouse/*-cp27-*-win32.whl')
        assert not glob('wheelhouse/*-cp34-*-win32.whl')
        assert glob('wheelhouse/*-cp35-*-win32.whl')
        assert glob('wheelhouse/*-cp36-*-win32.whl')
        assert glob('wheelhouse/*-cp37-*-win32.whl')
        assert not glob('wheelhouse/*-cp27-*-win_amd64.whl')
        assert not glob('wheelhouse/*-cp34-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp35-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp36-*-win_amd64.whl')
        assert glob('wheelhouse/*-cp37-*-win_amd64.whl')

    if utils.platform == 'macos':
        assert not glob('wheelhouse/*-cp27-*-macosx_10_6_intel.whl')
        assert not glob('wheelhouse/*-cp34-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp35-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp36-*-macosx_10_6_intel.whl')
        assert glob('wheelhouse/*-cp37-*-macosx_10_6_intel.whl')
