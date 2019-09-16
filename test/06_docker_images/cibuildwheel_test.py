import os, pytest
import utils

def test():
    project_dir = os.path.dirname(__file__)

    if utils.platform != 'linux':
        pytest.skip('the test is only relevant to the linux build')

    utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_MANYLINUX_X86_64_IMAGE': 'dockcross/manylinux2010-x64',
        'CIBW_MANYLINUX_I686_IMAGE': 'dockcross/manylinux1-x86',
        'CIBW_BEFORE_BUILD': '/opt/python/cp36-cp36m/bin/pip install -U auditwheel',  # Currently necessary on dockcross images to get auditwheel 2.1 supporting AUDITWHEEL_PLAT
        'CIBW_ENVIRONMENT': 'AUDITWHEEL_PLAT=`if [ $(uname -i) == "x86_64" ]; then echo "manylinux2010_x86_64"; else echo "manylinux1_i686"; fi`',
    })

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    actual_wheels = os.listdir('wheelhouse')
    assert set(actual_wheels) == set(expected_wheels)
