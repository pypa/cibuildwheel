import os, pytest, textwrap
from . import utils


def test(tmpdir):
    if utils.platform != "linux":
        pytest.skip("the docker test is only relevant to the linux build")

    project_dir = str(tmpdir)

    utils.generate_project(
        path=project_dir,
        spam_c_top_level_add=textwrap.dedent('''
            #include <malloc.h>
        '''),
        spam_c_function_add=textwrap.dedent('''
            malloc_info(0, stdout);
        ''')
    )
    
    # build the wheels
    # CFLAGS environment veriable is ecessary to fail on 'malloc_info' (on manylinux1) during compilation/linking,
    # rather than when dynamically loading the Python
    utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ENVIRONMENT": 'CFLAGS="$CFLAGS -Werror=implicit-function-declaration"',
        },
    )

    # also check that we got the right wheels
    expected_wheels = [
        w
        for w in utils.expected_wheels("spam", "0.1.0")
        if not "-manylinux" in w or "-manylinux2010" in w
    ]
    actual_wheels = os.listdir("wheelhouse")
    assert set(actual_wheels) == set(expected_wheels)
