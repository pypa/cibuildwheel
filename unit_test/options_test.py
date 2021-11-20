import platform as platform_module

import pytest

from cibuildwheel.__main__ import get_build_identifiers
from cibuildwheel.environment import parse_environment
from cibuildwheel.options import Options, _get_pinned_docker_images

from .utils import get_default_command_line_arguments

PYPROJECT_1 = """
[tool.cibuildwheel]
build = ["cp38*", "cp37*"]
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

    args = get_default_command_line_arguments()
    args.package_dir = str(tmp_path)

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    options = Options(platform="linux", command_line_arguments=args)

    identifiers = get_build_identifiers(
        platform="linux",
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    override_display = """\
test_command: 'pyproject'
  cp37-manylinux_x86_64: 'pyproject-override'"""

    print(options.summary(identifiers))

    assert override_display in options.summary(identifiers)

    default_build_options = options.build_options(identifier=None)

    assert default_build_options.environment == parse_environment('FOO="BAR"')

    all_pinned_docker_images = _get_pinned_docker_images()
    pinned_x86_64_docker_image = all_pinned_docker_images["x86_64"]

    local = options.build_options("cp38-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_docker_image["manylinux1"]

    local = options.build_options("cp37-manylinux_x86_64")
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject-override"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_docker_image["manylinux2014"]


def test_passthrough(tmp_path, monkeypatch):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    args = get_default_command_line_arguments()
    args.package_dir = str(tmp_path)

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")
    monkeypatch.setenv("EXAMPLE_ENV", "ONE")

    options = Options(platform="linux", command_line_arguments=args)

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
    args = get_default_command_line_arguments()
    args.package_dir = str(tmp_path)

    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")
    monkeypatch.setenv("CIBW_ENVIRONMENT_PASS_LINUX", "ENV_VAR")
    options = Options(platform="linux", command_line_arguments=args)

    monkeypatch.setenv("ENV_VAR", env_var_value)
    parsed_environment = options.build_options(identifier=None).environment
    assert parsed_environment.as_dictionary(prev_environment={}) == {"ENV_VAR": env_var_value}
