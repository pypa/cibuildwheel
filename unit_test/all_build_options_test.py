from pathlib import Path

from cibuildwheel.__main__ import get_build_identifiers
from cibuildwheel.environment import parse_environment
from cibuildwheel.options import _get_pinned_docker_images, compute_options
from cibuildwheel.util import AllBuildOptions

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


def test_all_build_options_1(tmp_path):
    with tmp_path.joinpath("pyproject.toml").open("w") as f:
        f.write(PYPROJECT_1)

    all_build_options, build_options_by_selector = compute_options(
        "linux", tmp_path, Path("dist"), None, None, False
    )

    identifiers = get_build_identifiers(
        "linux", all_build_options.build_selector, all_build_options.architectures
    )

    build_options = AllBuildOptions(all_build_options, build_options_by_selector, identifiers)

    override_display = """\
test_command:
  *: 'pyproject'
  cp37*: 'pyproject-override'"""

    assert override_display in str(build_options)

    assert build_options.environment == parse_environment('FOO="BAR"')

    all_pinned_docker_images = _get_pinned_docker_images()
    pinned_x86_64_docker_image = all_pinned_docker_images["x86_64"]

    local = build_options["cp38-manylinux_x86_64"]
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_docker_image["manylinux1"]

    local = build_options["cp37-manylinux_x86_64"]
    assert local.manylinux_images is not None
    assert local.test_command == "pyproject-override"
    assert local.manylinux_images["x86_64"] == pinned_x86_64_docker_image["manylinux2014"]
