import os, pytest
import utils

def test():
    project_dir = os.path.dirname(__file__)

    if utils.platform != 'linux':
        pytest.skip('the docker test is only relevant to the linux build')

    # build the wheels
    # CFLAGS environment veriable is ecessary to fail on 'malloc_info' (on manylinux1) during compilation/linking,
    # rather than when dynamically loading the Python
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ENVIRONMENT': 'CFLAGS="$CFLAGS -Werror=implicit-function-declaration"',
    })

    # also check that we got the right wheels
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if not '-manylinux' in w or '-manylinux2010' in w]
    assert set(actual_wheels) == set(expected_wheels)
