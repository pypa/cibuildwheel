import textwrap

import packaging.utils
import pytest

from cibuildwheel.logger import Logger
from cibuildwheel.selector import EnableGroup

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


@pytest.mark.serial
def test_dummy_serial():
    """A no-op test to ensure that at least one serial test is always found.

    Without this no-op test, CI fails on CircleCI because no serial tests are
    found, and pytest errors if a test suite finds no tests.
    """


def test(tmp_path, build_frontend_env, capfd):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=build_frontend_env)

    # check that the expected wheels are produced
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    actual_wheels_normalized = {packaging.utils.parse_wheel_filename(w) for w in actual_wheels}
    expected_wheels_normalized = {packaging.utils.parse_wheel_filename(w) for w in expected_wheels}
    assert actual_wheels_normalized == expected_wheels_normalized

    enable_groups = utils.get_enable_groups()
    if EnableGroup.GraalPy not in enable_groups:
        # Verify pip warning not shown
        captured = capfd.readouterr()
        for stream in (captured.err, captured.out):
            assert "WARNING: Running pip as the 'root' user can result" not in stream
            assert "A new release of pip available" not in stream


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


@pytest.mark.parametrize(
    "enable_setting", ["", "cpython-prerelease", "pypy", "cpython-freethreading"]
)
def test_build_identifiers(tmp_path, enable_setting, monkeypatch):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    monkeypatch.setenv("CIBW_ENABLE", enable_setting)

    # check that the number of expected wheels matches the number of build
    # identifiers
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    build_identifiers = utils.cibuildwheel_get_build_identifiers(project_dir)
    assert len(expected_wheels) == len(build_identifiers), (
        f"{expected_wheels} vs {build_identifiers}"
    )


@pytest.mark.parametrize(
    ("add_args", "env_allow_empty"),
    [
        (["--allow-empty"], {}),
        (["--allow-empty"], {"CIBW_ALLOW_EMPTY": "0"}),
        (None, {"CIBW_ALLOW_EMPTY": "1"}),
    ],
)
def test_allow_empty(tmp_path, add_args, env_allow_empty):
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    # Sanity check - --allow-empty should cause a no-op build to complete
    # without error
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={"CIBW_SKIP": "*", **env_allow_empty},
        add_args=add_args,
    )

    # check that nothing was built
    assert len(actual_wheels) == 0
