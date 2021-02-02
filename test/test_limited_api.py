import subprocess
import textwrap

import pytest

from . import test_projects, utils

limited_api_project = test_projects.new_c_project(
    setup_cfg_add=textwrap.dedent(r'''
        [bdist_wheel]
        py_limited_api=cp36
    ''')
)


def test_setup_cfg(tmp_path):
    project_dir = tmp_path / 'project'
    limited_api_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': 'cp27-* cp36-*',  # PyPy does not have a Py_LIMITED_API equivalent
    })

    # check that the expected wheels are produced
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', limited_api='cp36')
                       if '-pp' not in w]
    assert set(actual_wheels) == set(expected_wheels)


def test_build_option_env(tmp_path, capfd):
    project_dir = tmp_path / 'project'
    test_projects.new_c_project().generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ENVIRONMENT': 'PIP_BUILD_OPTION="--py-limited-api=cp36"',
        'CIBW_BUILD': 'cp27-* cp36-*',  # PyPy does not have a Py_LIMITED_API equivalent
    })

    # check that the expected wheels are produced
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0', limited_api='cp36')
                       if '-pp' not in w]
    assert set(actual_wheels) == set(expected_wheels)


def test_duplicate_wheel_error(tmp_path, capfd):
    project_dir = tmp_path / 'project'
    limited_api_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(project_dir, add_env={
            'CIBW_BUILD': 'cp36-* cp37-*',
        })

    captured = capfd.readouterr()
    print('out', captured.out)
    print('err', captured.err)
    assert "already exists in output directory" in captured.err
    assert "It looks like you are building wheels against Python's limited API" in captured.err
