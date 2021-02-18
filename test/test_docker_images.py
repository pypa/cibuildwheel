import platform
import textwrap

import pytest

from . import test_projects, utils

dockcross_only_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(r'''
        import os

        # check that we're running in the correct docker image as specified in the
        # environment options CIBW_MANYLINUX1_*_IMAGE
        if "linux" in sys.platform and not os.path.exists("/dockcross"):
            raise Exception(
                "/dockcross directory not found. Is this test running in the correct docker image?"
            )
    ''')
)


def test(tmp_path):
    if utils.platform != 'linux':
        pytest.skip('the test is only relevant to the linux build')
    if platform.machine() not in ['x86_64', 'i686']:
        pytest.skip('this test is currently only possible on x86_64/i686 due to availability of alternative images')

    project_dir = tmp_path / 'project'
    dockcross_only_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_MANYLINUX_X86_64_IMAGE': 'dockcross/manylinux2010-x64',
        'CIBW_MANYLINUX_I686_IMAGE': 'dockcross/manylinux2010-x86',
        'CIBW_SKIP': 'pp* cp27-* cp39-*',
    })

    # also check that we got the right wheels built
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                       if '-pp' not in w and '-cp39-' not in w and '-cp27-' not in w]
    assert set(actual_wheels) == set(expected_wheels)
