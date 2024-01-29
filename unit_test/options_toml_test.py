from __future__ import annotations

from pathlib import Path

import pytest

from cibuildwheel.options import ConfigOptionError, Inherit, OptionsReader, _dig_first

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

    assert options_reader.get("build", env_plat=False, sep=" ") == "cp39*"

    assert options_reader.get("test-command") == "pyproject"
    assert options_reader.get("archs", sep=" ") == "auto"
    assert (
        options_reader.get("test-requires", sep=" ")
        == {"windows": "something", "macos": "else", "linux": "other many"}[platform]
    )

    # Also testing options for support for both lists and tables
    assert (
        options_reader.get("environment", table={"item": '{k}="{v}"', "sep": " "})
        == 'THING="OTHER" FOO="BAR"'
    )
    assert (
        options_reader.get("environment", sep="x", table={"item": '{k}="{v}"', "sep": " "})
        == 'THING="OTHER" FOO="BAR"'
    )
    assert options_reader.get("test-extras", sep=",") == "one,two"
    assert (
        options_reader.get("test-extras", sep=",", table={"item": '{k}="{v}"', "sep": " "})
        == "one,two"
    )

    assert options_reader.get("manylinux-x86_64-image") == "manylinux1"
    assert options_reader.get("manylinux-i686-image") == "manylinux2014"

    with pytest.raises(ConfigOptionError):
        options_reader.get("environment", sep=" ")

    with pytest.raises(ConfigOptionError):
        options_reader.get("test-extras", table={"item": '{k}="{v}"', "sep": " "})


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

    assert options_reader.get("archs", sep=" ") == "auto"

    assert options_reader.get("build", sep=" ") == "cp38*"
    assert options_reader.get("manylinux-x86_64-image") == "manylinux_2_24"
    assert options_reader.get("manylinux-i686-image") == "manylinux2014"

    assert (
        options_reader.get("test-requires", sep=" ")
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

    assert options_reader.get("build", sep=", ") == "1, 2"
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
def test_dig_first(ignore_empty):
    d1 = {"random": "thing"}
    d2 = {"this": "that", "empty": ""}
    d3 = {"other": "hi"}
    d4 = {"this": "d4", "empty": "not"}

    answer = _dig_first(
        (d1, "empty", Inherit.NONE),
        (d2, "empty", Inherit.NONE),
        (d3, "empty", Inherit.NONE),
        (d4, "empty", Inherit.NONE),
        ignore_empty=ignore_empty,
    )
    assert answer == ("not" if ignore_empty else "")

    answer = _dig_first(
        (d1, "this", Inherit.NONE),
        (d2, "this", Inherit.NONE),
        (d3, "this", Inherit.NONE),
        (d4, "this", Inherit.NONE),
        ignore_empty=ignore_empty,
    )
    assert answer == "that"

    with pytest.raises(KeyError):
        _dig_first(
            (d1, "this", Inherit.NONE),
            (d2, "other", Inherit.NONE),
            (d3, "this", Inherit.NONE),
            (d4, "other", Inherit.NONE),
            ignore_empty=ignore_empty,
        )


@pytest.mark.parametrize("ignore_empty", [True, False], ids=["ignore_empty", "no_ignore_empty"])
@pytest.mark.parametrize("end", [Inherit.PREPEND, Inherit.NONE, Inherit.APPEND])
@pytest.mark.parametrize("append", [True, False], ids=["append", "prepend"])
def test_dig_first_merge_list(ignore_empty, end, append):
    d1 = {"random": ["thing"]}
    d2 = {"this": ["d2a", "d2b"], "empty": ""}
    d3 = {"other": ["hi"]}
    d4 = {"this": ["d4a", "d4b"], "empty": ["not"]}

    answer = _dig_first(
        (d1, "this", Inherit.NONE),
        (d2, "this", Inherit.APPEND if append else Inherit.PREPEND),
        (d3, "this", Inherit.NONE),
        (d4, "this", end),
        ignore_empty=ignore_empty,
    )

    assert answer == (["d4a", "d4b", "d2a", "d2b"] if append else ["d2a", "d2b", "d4a", "d4b"])


@pytest.mark.parametrize("ignore_empty", [True, False], ids=["ignore_empty", "no_ignore_empty"])
@pytest.mark.parametrize("end", [Inherit.PREPEND, Inherit.NONE, Inherit.APPEND])
def test_dig_first_merge_dict(ignore_empty, end):
    d1 = {"random": {"a": "thing"}}
    d2 = {"this": {"b": "that"}}
    d3 = {"other": {"c": "ho"}}
    d4 = {"this": {"d": "d4"}, "empty": {"d": "not"}}

    answer = _dig_first(
        (d1, "this", Inherit.NONE),
        (d2, "this", Inherit.APPEND),
        (d3, "this", Inherit.NONE),
        (d4, "this", end),
        ignore_empty=ignore_empty,
    )

    assert answer == {"b": "that", "d": "d4"}


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
    assert options_reader.get("test-command", sep=" && ") == "pyproject"

    with options_reader.identifier("random"):
        assert options_reader.get("test-command", sep=" && ") == "pyproject"

    with options_reader.identifier("cp37-something"):
        assert (
            options_reader.get("test-command", sep=" && ")
            == "pyproject-override && override2 && pyproject"
        )
        assert (
            options_reader.get("environment", table={"item": '{k}="{v}"', "sep": " "})
            == 'FOO="BAZ" HAM="EGGS" PYTHON="MONTY"'
        )

    with options_reader.identifier("cp37-final"):
        assert (
            options_reader.get("test-command", sep=" && ")
            == "extra-prepend && pyproject-override && override2 && pyproject && pyproject-finalize && finalize2 && extra-finalize"
        )
        assert (
            options_reader.get("environment", table={"item": '{k}="{v}"', "sep": " "})
            == 'FOO="BAZ" HAM="EGGS" PYTHON="MONTY"'
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
        options_reader.get("config-settings", table={"item": '{k}="{v}"', "sep": " "})
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
            "config-settings", table={"item": "--config-settings='{k}=\"{v}\"'", "sep": " "}
        )
        == "--config-settings='--build-option=\"--use-mypyc\"'"
    )
