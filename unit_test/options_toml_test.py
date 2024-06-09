from __future__ import annotations

from pathlib import Path

import pytest

from cibuildwheel.options import ConfigOptionError, InheritRule, OptionsReader, _resolve_cascade

PYPROJECT_1 = """
[tool.cibuildwheel]
build = "cp39*"
environment = {THING = "OTHER", FOO="BAR"}

test-command = "pyproject"
test-requires = "something"
test-extras = ["one", "two"]

manylinux-x86_64-image = "manylinux1"

[tool.cibuildwheel.macos]
test-requires = "else"

[tool.cibuildwheel.linux]
test-requires = ["other", "many"]
"""


@pytest.fixture(params=["linux", "macos", "windows"])
def platform(request):
    return request.param


@pytest.mark.parametrize("fname", ["pyproject.toml", "cibuildwheel.toml"])
def test_simple_settings(tmp_path, platform, fname):
    config_file_path: Path = tmp_path / fname
    config_file_path.write_text(PYPROJECT_1)

    options_reader = OptionsReader(config_file_path, platform=platform, env={})

    assert options_reader.get("build", env_plat=False, list_sep=" ") == "cp39*"

    assert options_reader.get("test-command") == "pyproject"
    assert options_reader.get("archs", list_sep=" ") == "auto"
    assert (
        options_reader.get("test-requires", list_sep=" ")
        == {"windows": "something", "macos": "else", "linux": "other many"}[platform]
    )

    # Also testing options for support for both lists and tables
    assert (
        options_reader.get("environment", table_format={"item": '{k}="{v}"', "sep": " "})
        == 'THING="OTHER" FOO="BAR"'
    )
    assert (
        options_reader.get(
            "environment", list_sep="x", table_format={"item": '{k}="{v}"', "sep": " "}
        )
        == 'THING="OTHER" FOO="BAR"'
    )
    assert options_reader.get("test-extras", list_sep=",") == "one,two"
    assert (
        options_reader.get(
            "test-extras", list_sep=",", table_format={"item": '{k}="{v}"', "sep": " "}
        )
        == "one,two"
    )

    assert options_reader.get("manylinux-x86_64-image") == "manylinux1"
    assert options_reader.get("manylinux-i686-image") == "manylinux2014"

    with pytest.raises(ConfigOptionError):
        options_reader.get("environment", list_sep=" ")

    with pytest.raises(ConfigOptionError):
        options_reader.get("test-extras", table_format={"item": '{k}="{v}"', "sep": " "})


def test_envvar_override(tmp_path, platform):
    config_file_path: Path = tmp_path / "pyproject.toml"
    config_file_path.write_text(PYPROJECT_1)

    options_reader = OptionsReader(
        config_file_path,
        platform=platform,
        env={
            "CIBW_BUILD": "cp38*",
            "CIBW_MANYLINUX_X86_64_IMAGE": "manylinux_2_24",
            "CIBW_TEST_COMMAND": "mytest",
            "CIBW_TEST_REQUIRES": "docs",
            "CIBW_TEST_REQUIRES_LINUX": "scod",
        },
    )

    assert options_reader.get("archs", list_sep=" ") == "auto"

    assert options_reader.get("build", list_sep=" ") == "cp38*"
    assert options_reader.get("manylinux-x86_64-image") == "manylinux_2_24"
    assert options_reader.get("manylinux-i686-image") == "manylinux2014"

    assert (
        options_reader.get("test-requires", list_sep=" ")
        == {"windows": "docs", "macos": "docs", "linux": "scod"}[platform]
    )
    assert options_reader.get("test-command") == "mytest"


def test_project_global_override_default_platform(tmp_path, platform):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
repair-wheel-command = "repair-project-global"
"""
    )
    options_reader = OptionsReader(pyproject_toml, platform=platform, env={})
    assert options_reader.get("repair-wheel-command") == "repair-project-global"


def test_env_global_override_default_platform(platform):
    options_reader = OptionsReader(
        platform=platform, env={"CIBW_REPAIR_WHEEL_COMMAND": "repair-env-global"}
    )
    assert options_reader.get("repair-wheel-command") == "repair-env-global"


def test_env_global_override_project_platform(tmp_path, platform):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel.linux]
repair-wheel-command = "repair-project-linux"
[tool.cibuildwheel.windows]
repair-wheel-command = "repair-project-windows"
[tool.cibuildwheel.macos]
repair-wheel-command = "repair-project-macos"
"""
    )
    options_reader = OptionsReader(
        pyproject_toml,
        platform=platform,
        env={
            "CIBW_REPAIR_WHEEL_COMMAND": "repair-env-global",
        },
    )
    assert options_reader.get("repair-wheel-command") == "repair-env-global"


def test_global_platform_order(tmp_path, platform):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel.linux]
repair-wheel-command = "repair-project-linux"
[tool.cibuildwheel.windows]
repair-wheel-command = "repair-project-windows"
[tool.cibuildwheel.macos]
repair-wheel-command = "repair-project-macos"
[tool.cibuildwheel]
repair-wheel-command = "repair-project-global"
"""
    )
    options_reader = OptionsReader(pyproject_toml, platform=platform, env={})
    assert options_reader.get("repair-wheel-command") == f"repair-project-{platform}"


def test_unexpected_key(tmp_path):
    # Note that platform contents are only checked when running
    # for that platform.
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
repairs-wheel-command = "repair-project-linux"
"""
    )

    with pytest.raises(ConfigOptionError) as excinfo:
        OptionsReader(pyproject_toml, platform="linux", env={})

    assert "repair-wheel-command" in str(excinfo.value)


def test_underscores_in_key(tmp_path):
    # Note that platform contents are only checked when running
    # for that platform.
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
repair_wheel_command = "repair-project-linux"
"""
    )

    with pytest.raises(ConfigOptionError) as excinfo:
        OptionsReader(pyproject_toml, platform="linux", env={})

    assert "repair-wheel-command" in str(excinfo.value)


def test_unexpected_table(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel.linus]
repair-wheel-command = "repair-project-linux"
"""
    )
    with pytest.raises(ConfigOptionError):
        OptionsReader(pyproject_toml, platform="linux", env={})


def test_unsupported_join(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
build = ["1", "2"]
"""
    )
    options_reader = OptionsReader(pyproject_toml, platform="linux", env={})

    assert options_reader.get("build", list_sep=", ") == "1, 2"
    with pytest.raises(ConfigOptionError):
        options_reader.get("build")


def test_disallowed_a(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel.windows]
manylinux-x86_64-image = "manylinux1"
"""
    )
    disallow = {"windows": {"manylinux-x86_64-image"}}
    OptionsReader(pyproject_toml, platform="linux", disallow=disallow, env={})
    with pytest.raises(ConfigOptionError):
        OptionsReader(pyproject_toml, platform="windows", disallow=disallow, env={})


def test_environment_override_empty(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
manylinux-i686-image = "manylinux1"
manylinux-x86_64-image = ""
"""
    )

    options_reader = OptionsReader(
        pyproject_toml,
        platform="linux",
        env={
            "CIBW_MANYLINUX_I686_IMAGE": "",
            "CIBW_MANYLINUX_AARCH64_IMAGE": "manylinux1",
        },
    )

    assert options_reader.get("manylinux-x86_64-image") == ""
    assert options_reader.get("manylinux-i686-image") == ""
    assert options_reader.get("manylinux-aarch64-image") == "manylinux1"

    assert options_reader.get("manylinux-x86_64-image", ignore_empty=True) == "manylinux2014"
    assert options_reader.get("manylinux-i686-image", ignore_empty=True) == "manylinux1"
    assert options_reader.get("manylinux-aarch64-image", ignore_empty=True) == "manylinux1"


@pytest.mark.parametrize("ignore_empty", [True, False], ids=["ignore_empty", "no_ignore_empty"])
def test_resolve_cascade(ignore_empty):
    answer = _resolve_cascade(
        ("not", InheritRule.NONE),
        (None, InheritRule.NONE),
        ("", InheritRule.NONE),
        (None, InheritRule.NONE),
        ignore_empty=ignore_empty,
    )
    assert answer == ("not" if ignore_empty else "")

    answer = _resolve_cascade(
        ("d4", InheritRule.NONE),
        (None, InheritRule.NONE),
        ("that", InheritRule.NONE),
        (None, InheritRule.NONE),
        ignore_empty=ignore_empty,
    )
    assert answer == "that"

    with pytest.raises(ValueError, match="a setting should at least have a default value"):
        _resolve_cascade(
            (None, InheritRule.NONE),
            (None, InheritRule.NONE),
            (None, InheritRule.NONE),
            (None, InheritRule.NONE),
            ignore_empty=ignore_empty,
        )


@pytest.mark.parametrize("ignore_empty", [True, False], ids=["ignore_empty", "no_ignore_empty"])
@pytest.mark.parametrize("rule", [InheritRule.PREPEND, InheritRule.NONE, InheritRule.APPEND])
def test_resolve_cascade_merge_list(ignore_empty, rule):
    answer = _resolve_cascade(
        (["a1", "a2"], InheritRule.NONE),
        ([], InheritRule.NONE),
        (["b1", "b2"], rule),
        (None, InheritRule.NONE),
        ignore_empty=ignore_empty,
        list_sep=" ",
    )

    if not ignore_empty:
        assert answer == "b1 b2"
    else:
        if rule == InheritRule.PREPEND:
            assert answer == "b1 b2 a1 a2"
        elif rule == InheritRule.NONE:
            assert answer == "b1 b2"
        elif rule == InheritRule.APPEND:
            assert answer == "a1 a2 b1 b2"


@pytest.mark.parametrize("rule", [InheritRule.PREPEND, InheritRule.NONE, InheritRule.APPEND])
def test_resolve_cascade_merge_dict(rule):
    answer = _resolve_cascade(
        ({"value": "a1", "base": "b1"}, InheritRule.NONE),
        (None, InheritRule.NONE),
        ({"value": "override"}, rule),
        (None, InheritRule.NONE),
        table_format={"item": "{k}={v}", "sep": " "},
    )

    if rule == InheritRule.PREPEND:
        assert answer == "value=override value=a1 base=b1"
    elif rule == InheritRule.NONE:
        assert answer == "value=override"
    elif rule == InheritRule.APPEND:
        assert answer == "value=a1 base=b1 value=override"


def test_resolve_cascade_merge_different_types():
    answer = _resolve_cascade(
        ({"value": "a1", "base": "b1"}, InheritRule.NONE),
        ({"value": "override"}, InheritRule.APPEND),
        table_format={"item": "{k}={v}", "sep": " "},
    )
    assert answer == "value=a1 base=b1 value=override"


PYPROJECT_2 = """
[tool.cibuildwheel]
build = ["cp38*", "cp37*"]
environment = {FOO="BAR", "HAM"="EGGS"}

test-command = ["pyproject"]

manylinux-x86_64-image = "manylinux1"

[tool.cibuildwheel.macos]
test-requires = "else"

[[tool.cibuildwheel.overrides]]
select = "cp37*"
inherit = {test-command="prepend", environment="append"}
test-command = ["pyproject-override", "override2"]
manylinux-x86_64-image = "manylinux2014"
environment = {FOO="BAZ", "PYTHON"="MONTY"}

[[tool.cibuildwheel.overrides]]
select = "*-final"
inherit = {test-command="append"}
test-command = ["pyproject-finalize", "finalize2"]

[[tool.cibuildwheel.overrides]]
select = "*-final"
inherit = {test-command="append"}
test-command = ["extra-finalize"]

[[tool.cibuildwheel.overrides]]
select = "*-final"
inherit = {test-command="prepend"}
test-command = ["extra-prepend"]
"""


def test_pyproject_2(tmp_path, platform):
    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(PYPROJECT_2)

    options_reader = OptionsReader(config_file_path=pyproject_toml, platform=platform, env={})
    assert options_reader.get("test-command", list_sep=" && ") == "pyproject"

    with options_reader.identifier("random"):
        assert options_reader.get("test-command", list_sep=" && ") == "pyproject"

    with options_reader.identifier("cp37-something"):
        assert (
            options_reader.get("test-command", list_sep=" && ")
            == "pyproject-override && override2 && pyproject"
        )
        assert (
            options_reader.get("environment", table_format={"item": '{k}="{v}"', "sep": " "})
            == 'FOO="BAR" HAM="EGGS" FOO="BAZ" PYTHON="MONTY"'
        )

    with options_reader.identifier("cp37-final"):
        assert (
            options_reader.get("test-command", list_sep=" && ")
            == "extra-prepend && pyproject-override && override2 && pyproject && pyproject-finalize && finalize2 && extra-finalize"
        )
        assert (
            options_reader.get("environment", table_format={"item": '{k}="{v}"', "sep": " "})
            == 'FOO="BAR" HAM="EGGS" FOO="BAZ" PYTHON="MONTY"'
        )


def test_overrides_not_a_list(tmp_path, platform):
    pyproject_toml: Path = tmp_path / "pyproject.toml"

    pyproject_toml.write_text(
        """\
[tool.cibuildwheel]
build = ["cp38*", "cp37*"]
[tool.cibuildwheel.overrides]
select = "cp37*"
test-command = "pyproject-override"
"""
    )

    with pytest.raises(ConfigOptionError):
        OptionsReader(config_file_path=pyproject_toml, platform=platform, env={})


def test_config_settings(tmp_path):
    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """\
[tool.cibuildwheel.config-settings]
example = "one"
other = ["two", "three"]
"""
    )

    options_reader = OptionsReader(config_file_path=pyproject_toml, platform="linux", env={})
    assert (
        options_reader.get("config-settings", table_format={"item": '{k}="{v}"', "sep": " "})
        == 'example="one" other="two" other="three"'
    )


def test_pip_config_settings(tmp_path):
    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """\
[tool.cibuildwheel.config-settings]
--build-option="--use-mypyc"
"""
    )

    options_reader = OptionsReader(config_file_path=pyproject_toml, platform="linux", env={})
    assert (
        options_reader.get(
            "config-settings", table_format={"item": "--config-settings='{k}=\"{v}\"'", "sep": " "}
        )
        == "--config-settings='--build-option=\"--use-mypyc\"'"
    )


def test_overrides_inherit(tmp_path):
    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """\
[tool.cibuildwheel]
before-all = ["before-all"]

[[tool.cibuildwheel.overrides]]
select = "cp37*"
inherit.before-all = "append"
before-all = ["override1"]

[[tool.cibuildwheel.overrides]]
select = "cp37*"
inherit.before-all = "prepend"
before-all = ["override2"]
"""
    )

    options_reader = OptionsReader(config_file_path=pyproject_toml, platform="linux", env={})
    with options_reader.identifier("cp38-something"):
        assert options_reader.get("before-all", list_sep=" && ") == "before-all"
    with options_reader.identifier("cp37-something"):
        assert (
            options_reader.get("before-all", list_sep=" && ")
            == "override2 && before-all && override1"
        )
