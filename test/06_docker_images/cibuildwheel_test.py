import os, pytest
import utils

def test():
    project_dir = os.path.dirname(__file__)

    if utils.platform != 'linux':
        pytest.skip('the test is only relevant to the linux build')

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_MANYLINUX_X86_64_IMAGE': 'dockcross/manylinux2010-x64',
        'CIBW_MANYLINUX_I686_IMAGE': 'dockcross/manylinux2010-x86',
    })

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
