import pytest

from cibuildwheel.options import ConfigNamespace, ConfigOptions

PYPROJECT_1 = """
[tool.cibuildwheel]
build = "cp39*"

[tool.cibuildwheel.manylinux]
x86_64-image = "manylinux1"

[tool.cibuildwheel.global]
test-command = "pyproject"
test-requires = "something"

[tool.cibuildwheel.macos]
test-requires = "else"

[tool.cibuildwheel.linux]
test-requires = "other"
"""


@pytest.fixture(params=["linux", "macos", "windows"])
def platform(request):
    return request.param


def test_simple_settings(tmp_path, platform):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    options = ConfigOptions(tmp_path, platform=platform)

    assert options("build", namespace=ConfigNamespace.MAIN) == "cp39*"
    assert options("output-dir", namespace=ConfigNamespace.MAIN) == "wheelhouse"

    assert options("test-command") == "pyproject"
    assert options("archs") == "auto"
    assert (
        options("test-requires")
        == {"windows": "something", "macos": "else", "linux": "other"}[platform]
    )

    assert options("x86_64-image", namespace=ConfigNamespace.MANYLINUX) == "manylinux1"
    assert options("i686-image", namespace=ConfigNamespace.MANYLINUX) == "manylinux2010"


def test_envvar_override(tmp_path, platform, monkeypatch):
    monkeypatch.setenv("CIBW_BUILD", "cp38*")
    monkeypatch.setenv("CIBW_MANYLINUX_X86_64_IMAGE", "manylinux2014")
    monkeypatch.setenv("CIBW_TEST_COMMAND", "mytest")
    monkeypatch.setenv("CIBW_TEST_REQUIRES", "docs")
    monkeypatch.setenv("CIBW_TEST_REQUIRES_LINUX", "scod")

    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    options = ConfigOptions(tmp_path, platform=platform)

    assert options("archs") == "auto"

    assert options("build", namespace=ConfigNamespace.MAIN) == "cp38*"
    assert options("x86_64-image", namespace=ConfigNamespace.MANYLINUX) == "manylinux2014"
    assert options("i686-image", namespace=ConfigNamespace.MANYLINUX) == "manylinux2010"

    assert (
        options("test-requires") == {"windows": "docs", "macos": "docs", "linux": "scod"}[platform]
    )
    assert options("test-command") == "mytest"
