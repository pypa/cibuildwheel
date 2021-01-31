import textwrap

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


def test_build_option_env(tmp_path):
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
