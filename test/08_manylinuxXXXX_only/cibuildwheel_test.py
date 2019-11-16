import os, pytest
import utils


@pytest.mark.parametrize('manylinux_image', ['manylinux1', 'manylinux2010', 'manylinux2014'])
def test(manylinux_image):
    project_dir = os.path.dirname(__file__)

    if utils.platform != 'linux':
        pytest.skip('the docker test is only relevant to the linux build')

    # build the wheels
    # CFLAGS environment variable is necessary to fail on 'malloc_info' (on manylinux1) during compilation/linking,
    # rather than when dynamically loading the Python
    add_env = {
        'CIBW_ENVIRONMENT': 'CFLAGS="$CFLAGS -Werror=implicit-function-declaration"',
        'CIBW_MANYLINUX_X86_64_IMAGE': manylinux_image,
        'CIBW_MANYLINUX_I686_IMAGE': manylinux_image,
    }
    if manylinux_image == 'manylinux2014':
        add_env['CIBW_SKIP'] = 'cp27*'  # not available on manylinux2014
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=add_env)

    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', manylinux_versions=[manylinux_image])]
    if manylinux_image == 'manylinux2014':
        expected_wheels = [w for w in expected_wheels if '-cp27' not in w]
    assert set(actual_wheels) == set(expected_wheels)
