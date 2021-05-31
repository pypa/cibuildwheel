import pytest

from cibuildwheel.options import ConfigOptions

PYPROJECT_1 = """
[tool.cibuildwheel]
build = "cp39*"
environment = {THING = "OTHER", FOO="BAR"}

test-command = "pyproject"
test-requires = "something"
test-extras = ["one", "two"]

[tool.cibuildwheel.manylinux]
x86_64-image = "manylinux1"

[tool.cibuildwheel.macos]
test-requires = "else"

[tool.cibuildwheel.linux]
test-requires = ["other", "many"]
"""


@pytest.fixture(params=["linux", "macos", "windows"])
def platform(request):
    return request.param


def test_simple_settings(tmp_path, platform):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    options = ConfigOptions(tmp_path, platform=platform)

    assert options("build", env_plat=False, sep=" ") == "cp39*"

    assert options("test-command") == "pyproject"
    assert options("archs", sep=" ") == "auto"
    assert (
        options("test-requires", sep=" ")
        == {"windows": "something", "macos": "else", "linux": "other many"}[platform]
    )

    assert options("environment", sep=" ") == 'THING="OTHER" FOO="BAR"'
    assert options("test-extras", sep=",") == "one,two"

    assert options("manylinux.x86_64-image") == "manylinux1"
    assert options("manylinux.i686-image") == "manylinux2010"


def test_envvar_override(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_BUILD", "cp38*")
    monkeypatch.setenv("CIBW_MANYLINUX_X86_64_IMAGE", "manylinux2014")
    monkeypatch.setenv("CIBW_TEST_COMMAND", "mytest")
    monkeypatch.setenv("CIBW_TEST_REQUIRES", "docs")
    monkeypatch.setenv("CIBW_TEST_REQUIRES_LINUX", "scod")

    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    options = ConfigOptions(tmp_path, platform=platform)

    assert options("archs", sep=" ") == "auto"

    assert options("build", sep=" ") == "cp38*"
    assert options("manylinux.x86_64-image") == "manylinux2014"
    assert options("manylinux.i686-image") == "manylinux2010"

    assert (
        options("test-requires", sep=" ")
        == {"windows": "docs", "macos": "docs", "linux": "scod"}[platform]
    )
    assert options("test-command") == "mytest"


def test_project_global_override_default_platform(tmp_path, platform):
    tmp_path.joinpath("pyproject.toml").write_text(
        """
[tool.cibuildwheel]
repair-wheel-command = "repair-project-global"
"""
    )
    options = ConfigOptions(tmp_path, platform=platform)
    assert options("repair-wheel-command") == "repair-project-global"


def test_env_global_override_default_platform(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", "repair-env-global")
    options = ConfigOptions(tmp_path, platform=platform)
    assert options("repair-wheel-command") == "repair-env-global"


def test_env_global_override_project_platform(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", "repair-env-global")
    tmp_path.joinpath("pyproject.toml").write_text(
        """
[tool.cibuildwheel.linux]
repair-wheel-command = "repair-project-linux"
[tool.cibuildwheel.windows]
repair-wheel-command = "repair-project-windows"
[tool.cibuildwheel.macos]
repair-wheel-command = "repair-project-macos"
"""
    )
    options = ConfigOptions(tmp_path, platform=platform)
    assert options("repair-wheel-command") == "repair-env-global"


def test_global_platform_order(tmp_path, platform):
    tmp_path.joinpath("pyproject.toml").write_text(
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
    options = ConfigOptions(tmp_path, platform=platform)
    assert options("repair-wheel-command") == f"repair-project-{platform}"
