import textwrap

from . import test_projects, utils

basic_project = test_projects.new_c_project(
    setup_cfg_add=textwrap.dedent(r'''
        [bdist_wheel]
        py_limited_api=cp36
    ''')
)


def test_setup_cfg(tmp_path):
    project_dir = tmp_path / 'project'
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': 'cp27-* cp36-* pp27-* pp36-*',
    })

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.1.0', limited_api='cp36')
    assert set(actual_wheels) == set(expected_wheels)
