import os, pytest, textwrap
from . import utils


@pytest.mark.parametrize('manylinux_image', ['manylinux1', 'manylinux2010', 'manylinux2014'])
def test(manylinux_image, tmpdir):
    if utils.platform != "linux":
        pytest.skip("the docker test is only relevant to the linux build")

    project_dir = str(tmpdir)

    utils.generate_project(
        path=project_dir,
        spam_c_top_level_add=textwrap.dedent('''
            #include <malloc.h>

            #if !defined(__GLIBC_PREREQ)
            #error "Must run on a glibc linux environment"
            #endif

            #if !__GLIBC_PREREQ(2, 5)  /* manylinux1 is glibc 2.5 */
            #error "Must run on a glibc >= 2.5 linux environment"
            #endif
        '''),
        spam_c_function_add=textwrap.dedent('''
            #if defined(__GLIBC_PREREQ) && __GLIBC_PREREQ(2, 17)  /* manylinux2014 is glibc 2.17 */
                // secure_getenv is only available in manylinux2014, ensuring
                // that only a manylinux2014 wheel is produced
                secure_getenv("NON_EXISTING_ENV_VARIABLE");
            #elif defined(__GLIBC_PREREQ) && __GLIBC_PREREQ(2, 10)  /* manylinux2010 is glibc 2.12 */
                // malloc_info is only available on manylinux2010+
                malloc_info(0, stdout);
            #endif
        ''')
    )
    
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
