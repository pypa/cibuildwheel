from pathlib import Path

import pytest

from cibuildwheel.options import ConfigOptionError, OptionsReader, _dig_first

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

    options_reader = OptionsReader(config_file_path, platform=platform)

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
    assert options_reader.get("manylinux-i686-image") == "manylinux2010"

    with pytest.raises(ConfigOptionError):
        options_reader.get("environment", sep=" ")

    with pytest.raises(ConfigOptionError):
        options_reader.get("test-extras", table={"item": '{k}="{v}"', "sep": " "})


def test_envvar_override(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_BUILD", "cp38*")
    monkeypatch.setenv("CIBW_MANYLINUX_X86_64_IMAGE", "manylinux2014")
    monkeypatch.setenv("CIBW_TEST_COMMAND", "mytest")
    monkeypatch.setenv("CIBW_TEST_REQUIRES", "docs")
    monkeypatch.setenv("CIBW_TEST_REQUIRES_LINUX", "scod")

    config_file_path: Path = tmp_path / "pyproject.toml"
    config_file_path.write_text(PYPROJECT_1)

    options_reader = OptionsReader(config_file_path, platform=platform)

    assert options_reader.get("archs", sep=" ") == "auto"

    assert options_reader.get("build", sep=" ") == "cp38*"
    assert options_reader.get("manylinux-x86_64-image") == "manylinux2014"
    assert options_reader.get("manylinux-i686-image") == "manylinux2010"

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
    options_reader = OptionsReader(pyproject_toml, platform=platform)
    assert options_reader.get("repair-wheel-command") == "repair-project-global"


def test_env_global_override_default_platform(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", "repair-env-global")
    options_reader = OptionsReader(platform=platform)
    assert options_reader.get("repair-wheel-command") == "repair-env-global"


def test_env_global_override_project_platform(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", "repair-env-global")
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
    options_reader = OptionsReader(pyproject_toml, platform=platform)
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
    options_reader = OptionsReader(pyproject_toml, platform=platform)
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

    with pytest.raises(ConfigOptionError):
        OptionsReader(pyproject_toml, platform="linux")


def test_unexpected_table(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel.linus]
repair-wheel-command = "repair-project-linux"
"""
    )
    with pytest.raises(ConfigOptionError):
        OptionsReader(pyproject_toml, platform="linux")


def test_unsupported_join(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
build = ["1", "2"]
"""
    )
    options_reader = OptionsReader(pyproject_toml, platform="linux")

    assert "1, 2" == options_reader.get("build", sep=", ")
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
    OptionsReader(pyproject_toml, platform="linux", disallow=disallow)
    with pytest.raises(ConfigOptionError):
        OptionsReader(pyproject_toml, platform="windows", disallow=disallow)


def test_environment_override_empty(tmp_path, monkeypatch):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
[tool.cibuildwheel]
manylinux-i686-image = "manylinux1"
manylinux-x86_64-image = ""
"""
    )

    monkeypatch.setenv("CIBW_MANYLINUX_I686_IMAGE", "")
    monkeypatch.setenv("CIBW_MANYLINUX_AARCH64_IMAGE", "manylinux1")

    options_reader = OptionsReader(pyproject_toml, platform="linux")

    assert options_reader.get("manylinux-x86_64-image") == ""
    assert options_reader.get("manylinux-i686-image") == ""
    assert options_reader.get("manylinux-aarch64-image") == "manylinux1"

    assert options_reader.get("manylinux-x86_64-image", ignore_empty=True) == "manylinux2010"
    assert options_reader.get("manylinux-i686-image", ignore_empty=True) == "manylinux1"
    assert options_reader.get("manylinux-aarch64-image", ignore_empty=True) == "manylinux1"


@pytest.mark.parametrize("ignore_empty", (True, False))
def test_dig_first(ignore_empty):
    d1 = {"random": "thing"}
    d2 = {"this": "that", "empty": ""}
    d3 = {"other": "hi"}
    d4 = {"this": "d4", "empty": "not"}

    answer = _dig_first(
        (d1, "empty"),
        (d2, "empty"),
        (d3, "empty"),
        (d4, "empty"),
        ignore_empty=ignore_empty,
    )
    assert answer == ("not" if ignore_empty else "")

    answer = _dig_first(
        (d1, "this"),
        (d2, "this"),
        (d3, "this"),
        (d4, "this"),
        ignore_empty=ignore_empty,
    )
    assert answer == "that"

    with pytest.raises(KeyError):
        _dig_first(
            (d1, "this"),
            (d2, "other"),
            (d3, "this"),
            (d4, "other"),
            ignore_empty=ignore_empty,
        )


PYPROJECT_2 = """
[tool.cibuildwheel]
build = ["cp38*", "cp37*"]
environment = {FOO="BAR"}

test-command = "pyproject"

manylinux-x86_64-image = "manylinux1"

[tool.cibuildwheel.macos]
test-requires = "else"

[[tool.cibuildwheel.overrides]]
select = "cp37*"
test-command = "pyproject-override"
manylinux-x86_64-image = "manylinux2014"
"""


def test_pyproject_2(tmp_path, platform):
    pyproject_toml: Path = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(PYPROJECT_2)

    options_reader = OptionsReader(config_file_path=pyproject_toml, platform=platform)
    assert options_reader.get("test-command") == "pyproject"

    with options_reader.identifier("random"):
        assert options_reader.get("test-command") == "pyproject"

    with options_reader.identifier("cp37-something"):
        assert options_reader.get("test-command") == "pyproject-override"


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
        OptionsReader(config_file_path=pyproject_toml, platform=platform)
