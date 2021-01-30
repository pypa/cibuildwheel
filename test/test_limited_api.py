from . import test_projects, utils

basic_project = test_projects.new_c_project(
    setup_py_setup_args_add='py_limited_api=True',
)


def test_setup_py(tmp_path):
    project_dir = tmp_path / 'project'
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': 'cp27-* cp35-*',
    })

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels('spam', '0.1.0', limited_api=True)
    assert set(actual_wheels) == set(expected_wheels)
