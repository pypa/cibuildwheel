import pytest
import os 
import sys
import subprocess 
import utils 


def test_wrong_identifier_py2():
    if sys.version_info[0] != 2:
        pytest.skip("test for python 2.7")
    project_dir = os.path.dirname(__file__)

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        utils.cibuildwheel_run(project_dir, add_env={'CIBW_BUILD':'py368-*'})
    
def test_wrong_identifier():
    if sys.version_info[0] == 2:
        pytest.skip("test not running on python 2.7")
    project_dir = os.path.dirname(__file__)
    env = os.environ.copy()
    env['CIBW_BUILD'] = 'py368-*'
    
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        subprocess.run(
            [sys.executable, '-m', 'cibuildwheel', project_dir],
            env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True
        )

    assert "Check 'CIBW_BUILD' and 'CIBW_SKIP' environment variables." in excinfo.value.stderr

def test_old_manylinux():
    if sys.version_info[0] == 2:
        pytest.skip("test not running on python 2.7")
    if sys.version_info[0] == 3 and sys.version_info[1] == 4:
        pytest.skip("test not running on python 3.4")
    if utils.platform != 'linux':
        pytest.skip('the old manylinux test is only relevant to the linux build')

    project_dir = os.path.dirname(__file__)

    env = os.environ.copy()
    env['CIBW_BUILD'] = "*-manylinux1_x86_64 py36-*"
    
    res = subprocess.run(
        [sys.executable, '-m', 'cibuildwheel', project_dir],
        env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    assert "Build identifiers with 'manylinux1' been deprecated. Replacing all occurences of"\
           " 'manylinux1' by 'manylinux' in the option 'CIBW_BUILD'" in res.stderr