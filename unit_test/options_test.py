import platform as platform_module

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
