import textwrap

import pytest

from cibuildwheel.logger import Logger

from . import test_projects, utils

basic_project = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        """
        import os

        if os.environ.get("CIBUILDWHEEL", "0") != "1":
            raise Exception("CIBUILDWHEEL environment variable is not set to 1")
        """
    )
)


def test(tmp_path, build_frontend_env):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=build_frontend_env)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.skip(reason="to keep test output clean")
def test_sample_build(tmp_path, capfd):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels, and let the output passthrough to the caller, so
    # we can see how it looks
    with capfd.disabled():
        logger = Logger()
        logger.step("test_sample_build")
        try:
            utils.cibuildwheel_run(project_dir)
        finally:
            logger.step_end()


def test_build_identifiers(tmp_path):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # check that the number of expected wheels matches the number of build
    # identifiers
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    build_identifiers = utils.cibuildwheel_get_build_identifiers(
        project_dir, prerelease_pythons=True
    )
    assert len(expected_wheels) == len(build_identifiers)
