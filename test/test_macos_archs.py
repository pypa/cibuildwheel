import pytest

from . import test_projects, utils

basic_project = test_projects.new_c_project()


def test_cross_compiled_build(tmp_path):
    if utils.platform != 'macos':
        pytest.skip('this test is only relevant to macos')
    if utils.get_macos_version() < (11, 0):
        pytest.skip('this test only works on macOS 11 or greater')

    project_dir = tmp_path / 'project'
    basic_project.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ARCHS': 'x86_64, universal2, arm64',
    })

    expected_wheels = (
        utils.expected_wheels('spam', '0.1.0', machine_arch='x86_64')
        + utils.expected_wheels('spam', '0.1.0', machine_arch='arm64')
    )
    assert set(actual_wheels) == set(expected_wheels)

# TODO: add a TEST_COMMAND test when using cross-compiling
