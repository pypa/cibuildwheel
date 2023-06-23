from __future__ import annotations

import os
import platform as platform_module
import textwrap
from pathlib import Path

import pytest

from cibuildwheel.__main__ import get_build_identifiers, get_platform_module
from cibuildwheel.bashlex_eval import local_environment_executor
from cibuildwheel.environment import parse_environment
from cibuildwheel.options import (
    CommandLineArguments,
    Options,
    _get_pinned_container_images,
)

PYPROJECT_1 = """
[tool.cibuildwheel]
build = ["cp38*", "cp37*"]
skip = ["*musllinux*"]
environment = {FOO="BAR"}

test-command = "pyproject"

manylinux-x86_64-image = "manylinux1"

environment-pass = ["EXAMPLE_ENV"]

[tool.cibuildwheel.macos]
test-requires = "else"

[[tool.cibuildwheel.overrides]]
select = "cp37*"
test-command = "pyproject-override"
manylinux-x86_64-image = "manylinux2014"
"""


def test_options_1(tmp_path, monkeypatch):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    options = Options(platform="linux", command_line_arguments=args, env={})

    module = get_platform_module("linux")
    identifiers = get_build_identifiers(
        platform_module=module,
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    override_display = """\
  *: pyproject
  cp37-manylinux_x86_64, cp37-manylinux_i686: pyproject-override"""
    print(options.summary(identifiers))

    assert override_display in options.summary(identifiers)

    default_build_options = options.build_options(identifier=None)

    assert default_build_options.environment == parse_environment('FOO="BAR"')

    all_pinned_container_images = _get_pinned_container_images()
    pinned_x86_64_container_image = all_pinned_container_images["x86_64"]

    local = options.build_options("cp38-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_container_image["manylinux1"]

    local = options.build_options("cp37-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject-override"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_container_image["manylinux2014"]


def test_passthrough(tmp_path, monkeypatch):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    options = Options(platform="linux", command_line_arguments=args, env={"EXAMPLE_ENV": "ONE"})

    default_build_options = options.build_options(identifier=None)

    assert default_build_options.environment.as_dictionary(prev_environment={}) == {
        "FOO": "BAR",
        "EXAMPLE_ENV": "ONE",
    }


@pytest.mark.parametrize(
    "env_var_value",
    [
        "normal value",
        '"value wrapped in quotes"',
        "an unclosed single-quote: '",
        'an unclosed double-quote: "',
        "string\nwith\ncarriage\nreturns\n",
        "a trailing backslash \\",
    ],
)
def test_passthrough_evil(tmp_path, monkeypatch, env_var_value):
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")
    options = Options(
        platform="linux",
        command_line_arguments=args,
        env={"CIBW_ENVIRONMENT_PASS_LINUX": "ENV_VAR", "ENV_VAR": env_var_value},
    )

    parsed_environment = options.build_options(identifier=None).environment
    assert parsed_environment.as_dictionary(prev_environment={}) == {"ENV_VAR": env_var_value}


xfail_env_parse = pytest.mark.xfail(
    raises=SystemExit, reason="until we can figure out the right way to quote these values"
)


@pytest.mark.parametrize(
    "env_var_value",
    [
        "normal value",
        pytest.param('"value wrapped in quotes"', marks=[xfail_env_parse]),
        pytest.param('an unclosed double-quote: "', marks=[xfail_env_parse]),
        "string\nwith\ncarriage\nreturns\n",
        pytest.param("a trailing backslash \\", marks=[xfail_env_parse]),
    ],
)
def test_toml_environment_evil(tmp_path, env_var_value):
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    tmp_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel.environment]
            EXAMPLE='''{env_var_value}'''
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={})
    parsed_environment = options.build_options(identifier=None).environment
    assert parsed_environment.as_dictionary(prev_environment={}) == {"EXAMPLE": env_var_value}


@pytest.mark.parametrize(
    ("toml_assignment", "result_value"),
    [
        ('TEST_VAR="simple_value"', "simple_value"),
        # spaces
        ('TEST_VAR="simple value"', "simple value"),
        # env var
        ('TEST_VAR="$PARAM"', "spam"),
        ('TEST_VAR="$PARAM $PARAM"', "spam spam"),
        # env var extension
        ('TEST_VAR="before:$PARAM:after"', "before:spam:after"),
        # env var extension with spaces
        ('TEST_VAR="before $PARAM after"', "before spam after"),
        # literal $ - this test is just for reference, I'm not sure if this
        # syntax will work if we change the TOML quoting behaviour
        (r'TEST_VAR="before\\$after"', "before$after"),
    ],
)
def test_toml_environment_quoting(tmp_path: Path, toml_assignment, result_value):
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    tmp_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel.environment]
            {toml_assignment}
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={})
    parsed_environment = options.build_options(identifier=None).environment
    environment_values = parsed_environment.as_dictionary(
        prev_environment={**os.environ, "PARAM": "spam"},
        executor=local_environment_executor,
    )

    assert environment_values["TEST_VAR"] == result_value


@pytest.mark.parametrize(
    ("toml_assignment", "result_name", "result_create_args"),
    [
        (
            'container-engine = "podman"',
            "podman",
            [],
        ),
        (
            'container-engine = {name = "podman"}',
            "podman",
            [],
        ),
        (
            'container-engine = "docker; create_args: --some-option"',
            "docker",
            ["--some-option"],
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option"]}',
            "docker",
            ["--some-option"],
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option", "value that contains spaces"]}',
            "docker",
            ["--some-option", "value that contains spaces"],
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option", "value;that;contains;semicolons"]}',
            "docker",
            ["--some-option", "value;that;contains;semicolons"],
        ),
    ],
)
def test_container_engine_option(tmp_path: Path, toml_assignment, result_name, result_create_args):
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    tmp_path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel]
            {toml_assignment}
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={})
    parsed_container_engine = options.globals.container_engine

    assert parsed_container_engine.name == result_name
    assert parsed_container_engine.create_args == result_create_args
