import os
import platform as platform_module
import textwrap
import unittest.mock
from pathlib import Path
from typing import Literal

import pytest

from cibuildwheel import errors
from cibuildwheel.bashlex_eval import local_environment_executor
from cibuildwheel.frontend import BuildFrontendConfig, get_build_frontend_extra_flags
from cibuildwheel.logger import Logger
from cibuildwheel.options import (
    CommandLineArguments,
    Options,
    _get_pinned_container_images,
)
from cibuildwheel.platforms import ALL_PLATFORM_MODULES, get_build_identifiers
from cibuildwheel.selector import EnableGroup
from cibuildwheel.util import resources
from cibuildwheel.util.packaging import DependencyConstraints

PYPROJECT_1 = """
[tool.cibuildwheel]
build = ["cp38-*", "cp313-*"]
skip = ["*musllinux*"]
environment = {FOO="BAR"}

test-command = "pyproject"
test-sources = ["test", "other dir"]

manylinux-x86_64-image = "manylinux_2_28"

environment-pass = ["EXAMPLE_ENV"]

pyodide-version = "0.27.6"

[tool.cibuildwheel.macos]
test-requires = "else"

[[tool.cibuildwheel.overrides]]
select = "cp313-*"
test-command = "pyproject-override"
manylinux-x86_64-image = "manylinux_2_34"
"""


def test_options_1(tmp_path, monkeypatch):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    options = Options(platform="linux", command_line_arguments=args, env={})

    module = ALL_PLATFORM_MODULES["linux"]
    identifiers = get_build_identifiers(
        platform_module=module,
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    override_display = """\
  *: pyproject
  cp313-manylinux_x86_64, cp313-manylinux_i686: pyproject-override"""
    print(options.summary(identifiers))

    assert override_display in options.summary(identifiers)

    default_build_options = options.build_options(identifier=None)

    assert default_build_options.environment.as_dictionary(prev_environment={}) == {"FOO": "BAR"}

    all_pinned_container_images = _get_pinned_container_images()
    pinned_x86_64_container_image = all_pinned_container_images["x86_64"]

    local = options.build_options("cp38-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject"
    assert local.test_sources == ["test", "other dir"]
    assert local.manylinux_images["x86_64"] == pinned_x86_64_container_image["manylinux_2_28"]

    local = options.build_options("cp313-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject-override"
    assert local.test_sources == ["test", "other dir"]
    assert local.manylinux_images["x86_64"] == pinned_x86_64_container_image["manylinux_2_34"]

    local = options.build_options("cp312-pyodide_wasm32")
    assert local.pyodide_version == "0.27.6"


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
    raises=errors.ConfigurationError,
    reason="until we can figure out the right way to quote these values",
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
def test_toml_environment_quoting(tmp_path: Path, toml_assignment: str, result_value: str) -> None:
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
    ("toml_assignment", "result_name", "result_create_args", "result_disable_host_mount"),
    [
        (
            'container-engine = "podman"',
            "podman",
            (),
            False,
        ),
        (
            'container-engine = {name = "podman"}',
            "podman",
            (),
            False,
        ),
        (
            'container-engine = "docker; create_args: --some-option"',
            "docker",
            ("--some-option",),
            False,
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option"]}',
            "docker",
            ("--some-option",),
            False,
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option", "value that contains spaces"]}',
            "docker",
            ("--some-option", "value that contains spaces"),
            False,
        ),
        (
            'container-engine = {name = "docker", create-args = ["--some-option", "value;that;contains;semicolons"]}',
            "docker",
            ("--some-option", "value;that;contains;semicolons"),
            False,
        ),
        (
            'container-engine = {name = "docker", disable-host-mount = true}',
            "docker",
            (),
            True,
        ),
        (
            'container-engine = {name = "docker", disable_host_mount = true}',
            "docker",
            (),
            True,
        ),
    ],
)
def test_container_engine_option(
    tmp_path: Path,
    toml_assignment: str,
    result_name: str,
    result_create_args: tuple[str, ...],
    result_disable_host_mount: bool,
) -> None:
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
    parsed_container_engine = options.build_options(None).container_engine

    assert parsed_container_engine.name == result_name
    assert parsed_container_engine.create_args == result_create_args
    assert parsed_container_engine.disable_host_mount == result_disable_host_mount


def test_environment_pass_references():
    options = Options(
        platform="linux",
        command_line_arguments=CommandLineArguments.defaults(),
        env={
            "CIBW_ENVIRONMENT_PASS_LINUX": "STARTER MAIN_COURSE",
            "STARTER": "green eggs",
            "MAIN_COURSE": "ham",
            "CIBW_ENVIRONMENT": 'MEAL="$STARTER and $MAIN_COURSE"',
        },
    )
    parsed_environment = options.build_options(identifier=None).environment
    assert parsed_environment.as_dictionary(prev_environment={}) == {
        "MEAL": "green eggs and ham",
        "STARTER": "green eggs",
        "MAIN_COURSE": "ham",
    }


@pytest.mark.parametrize(
    ("toml_assignment", "result_name", "result_args"),
    [
        (
            "",
            None,
            None,
        ),
        (
            'build-frontend = "build"',
            "build",
            [],
        ),
        (
            'build-frontend = {name = "build"}',
            "build",
            [],
        ),
        (
            'build-frontend = "pip; args: --some-option"',
            "pip",
            ["--some-option"],
        ),
        (
            'build-frontend = {name = "pip", args = ["--some-option"]}',
            "pip",
            ["--some-option"],
        ),
    ],
)
def test_build_frontend_option(
    tmp_path: Path, toml_assignment: str, result_name: str, result_args: list[str]
) -> None:
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
    parsed_build_frontend = options.build_options(identifier=None).build_frontend

    if toml_assignment:
        assert parsed_build_frontend is not None
        assert parsed_build_frontend.name == result_name
        assert parsed_build_frontend.args == result_args
    else:
        assert parsed_build_frontend is None


def test_override_inherit_environment(tmp_path: Path) -> None:
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.cibuildwheel]
            environment = {FOO="BAR", "HAM"="EGGS"}

            [[tool.cibuildwheel.overrides]]
            select = "cp37*"
            inherit.environment = "append"
            environment = {FOO="BAZ", "PYTHON"="MONTY"}
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={})
    parsed_environment = options.build_options(identifier=None).environment
    assert parsed_environment.as_dictionary(prev_environment={}) == {
        "FOO": "BAR",
        "HAM": "EGGS",
    }

    assert options.build_options("cp37-manylinux_x86_64").environment.as_dictionary(
        prev_environment={}
    ) == {
        "FOO": "BAZ",
        "HAM": "EGGS",
        "PYTHON": "MONTY",
    }


def test_override_inherit_environment_with_references(tmp_path: Path) -> None:
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """\
            [tool.cibuildwheel]
            environment = {PATH="/opt/bin:$PATH"}

            [[tool.cibuildwheel.overrides]]
            select = "cp37*"
            inherit.environment = "append"
            environment = {PATH="/opt/local/bin:$PATH"}
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={"MONTY": "PYTHON"})
    parsed_environment = options.build_options(identifier=None).environment
    prev_environment = {"PATH": "/usr/bin:/bin"}
    assert parsed_environment.as_dictionary(prev_environment=prev_environment) == {
        "PATH": "/opt/bin:/usr/bin:/bin",
    }

    assert options.build_options("cp37-manylinux_x86_64").environment.as_dictionary(
        prev_environment=prev_environment
    ) == {
        "PATH": "/opt/local/bin:/opt/bin:/usr/bin:/bin",
    }


@pytest.mark.parametrize(
    ("toml_assignment", "env", "enable_args", "expected_result"),
    [
        ("", {}, [], False),
        ("enable = ['cpython-freethreading']", {}, [], True),
        ("enable = []", {}, [], False),
        ("", {}, ["cpython-freethreading"], True),
        ("", {}, ["cpython-freethreading", "pypy"], True),
        ("", {"CIBW_ENABLE": "pypy"}, [], False),
        ("", {"CIBW_ENABLE": "cpython-freethreading"}, [], True),
        ("enable = []", {"CIBW_ENABLE": "cpython-freethreading"}, [], True),
        ("enable = ['cpython-freethreading']", {"CIBW_ENABLE": "pypy"}, [], True),
        ("enable = ['cpython-freethreading']", {}, ["pypy"], True),
        ("enable = ['cpython-freethreading']", {"CIBW_ENABLE": ""}, [], True),
        ("enable = []", {"CIBW_ENABLE": ""}, [], False),
    ],
)
def test_free_threaded_support(
    tmp_path: Path,
    toml_assignment: str,
    env: dict[str, str],
    enable_args: list[str],
    expected_result: bool,
) -> None:
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path
    args.enable = enable_args

    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel]
            {toml_assignment}
            """
        )
    )
    options = Options(platform="linux", command_line_arguments=args, env=env)
    if expected_result:
        assert EnableGroup.CPythonFreeThreading in options.globals.build_selector.enable
    else:
        assert EnableGroup.CPythonFreeThreading not in options.globals.build_selector.enable


@pytest.mark.parametrize(
    ("toml_assignment", "base_file_path", "packages"),
    [
        ("", resources.CONSTRAINTS, []),
        ("dependency-versions = 'pinned'", resources.CONSTRAINTS, []),
        ("dependency-versions = 'latest'", None, []),
        ("dependency-versions = 'constraints file.txt'", Path("constraints file.txt"), []),
        (
            "dependency-versions = \"file:'constraints file.txt'\"",
            Path("constraints file.txt"),
            [],
        ),
        (
            "dependency-versions = {file = 'constraints file.txt'}",
            Path("constraints file.txt"),
            [],
        ),
        (
            "dependency-versions = 'packages: foo==1.2.3 bar==4.5.6'",
            None,
            ["foo==1.2.3", "bar==4.5.6"],
        ),
    ],
)
def test_dependency_versions_toml(
    tmp_path: Path,
    toml_assignment: str,
    base_file_path: Path | None,
    packages: list[str] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    (tmp_path / "constraints file.txt").write_text("")
    monkeypatch.chdir(tmp_path)

    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel]
            {toml_assignment}
            """
        )
    )

    options = Options(platform="linux", command_line_arguments=args, env={})
    parsed_dependency_constraints = options.build_options(None).dependency_constraints
    if base_file_path is None and packages is None:
        assert parsed_dependency_constraints == DependencyConstraints.latest()
    else:
        if parsed_dependency_constraints.base_file_path and base_file_path:
            assert parsed_dependency_constraints.base_file_path.samefile(base_file_path)
        else:
            assert parsed_dependency_constraints.base_file_path == base_file_path
        assert parsed_dependency_constraints.packages == packages


@pytest.mark.parametrize(
    ("image", "deprecated", "raises"),
    [
        ("manylinux1", True, True),
        ("manylinux2010", True, True),
        ("manylinux2014", False, False),
        ("manylinux_2_24", True, True),
        ("manylinux_2_28", False, False),
        ("manylinux_2_34", False, False),
        ("musllinux_1_1", True, True),
        ("musllinux_1_2", False, False),
    ],
)
def test_deprecated_image(
    image: str, deprecated: bool, raises: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not raises or deprecated
    args = CommandLineArguments.defaults()
    env = {
        "CIBW_ARCHS": "x86_64",
        "CIBW_MANYLINUX_X86_64_IMAGE": image if image.startswith("manylinux") else "",
        "CIBW_MUSLLINUX_X86_64_IMAGE": image if image.startswith("musllinux") else "",
    }
    options = Options(platform="linux", command_line_arguments=args, env=env)
    try:
        bo = options.build_options(None)
        assert not raises
    except errors.DeprecationError:
        assert raises
        return
    images = bo.manylinux_images if image.startswith("manylinux") else bo.musllinux_images
    assert images is not None
    resolved_image = images["x86_64"]
    captured = capsys.readouterr()
    if deprecated:
        assert f"Deprecated image {image!r}" in captured.err
        assert f"{resolved_image!r}" in captured.err
    else:
        assert "Deprecated image" not in captured.err


@pytest.mark.parametrize(
    ("frontend", "verbosity", "result"),
    [
        ("pip", 3, ["-Ca", "-Cb", "-1", "-vvv"]),
        ("pip", 2, ["-Ca", "-Cb", "-1", "-vv"]),
        ("pip", -1, ["-Ca", "-Cb", "-1", "-q"]),
        ("build", 0, ["-Ca", "-Cb", "-1"]),
        ("build", 1, ["-Ca", "-Cb", "-1"]),
        ("build", 2, ["-Ca", "-Cb", "-1", "-v"]),
        ("build", 3, ["-Ca", "-Cb", "-1", "-vv"]),
        ("build[uv]", 3, ["-Ca", "-Cb", "-1", "-vv"]),
    ],
)
def test_get_build_frontend_extra_flags(
    frontend: Literal["pip", "build", "build[uv]"],
    verbosity: int,
    result: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_warning = unittest.mock.MagicMock()
    monkeypatch.setattr(Logger, "warning", mock_warning)
    build_frontend = BuildFrontendConfig(frontend, ["-1"])
    args = get_build_frontend_extra_flags(
        build_frontend=build_frontend, verbosity_level=verbosity, config_settings="a b"
    )

    assert args == result
    mock_warning.assert_not_called()


@pytest.mark.parametrize("frontend", ["build", "build[uv]"])
def test_get_build_frontend_extra_flags_warning(
    frontend: Literal["build", "build[uv]"], monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_warning = unittest.mock.MagicMock()
    monkeypatch.setattr(Logger, "warning", mock_warning)
    build_frontend = BuildFrontendConfig(frontend, ["-1"])
    args = get_build_frontend_extra_flags(
        build_frontend=build_frontend, verbosity_level=-1, config_settings="a b"
    )
    assert args == ["-Ca", "-Cb", "-1"]
    mock_warning.assert_called_once()


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        ("", None),
        ("xbuild-tools = []", []),
        ('xbuild-tools = ["cmake", "rustc"]', ["cmake", "rustc"]),
    ],
)
def test_xbuild_tools_handling(tmp_path: Path, definition: str, expected: list[str] | None) -> None:
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path

    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            f"""\
            [tool.cibuildwheel]
            {definition}
            """
        )
    )

    options = Options(platform="ios", command_line_arguments=args, env={})

    local = options.build_options("cp313-ios_13_0_arm64_iphoneos")
    assert local.xbuild_tools == expected
