import textwrap
from pathlib import Path
from pprint import pprint

import cibuildwheel.linux
import cibuildwheel.oci_container
from cibuildwheel.options import Options

from .utils import get_default_command_line_arguments


def test_linux_container_split(tmp_path: Path, monkeypatch):
    """
    Tests splitting linux builds by container image and before_all
    """

    args = get_default_command_line_arguments()
    args.platform = "linux"

    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
                [tool.cibuildwheel]
                manylinux-x86_64-image = "normal_container_image"
                manylinux-i686-image = "normal_container_image"
                build = "*-manylinux_x86_64"
                skip = "pp*"
                archs = "x86_64 i686"

                [[tool.cibuildwheel.overrides]]
                select = "cp{38,39,310}-*"
                manylinux-x86_64-image = "other_container_image"
                manylinux-i686-image = "other_container_image"

                [[tool.cibuildwheel.overrides]]
                select = "cp39-*"
                before-all = "echo 'a cp39-only command'"
            """
        )
    )

    monkeypatch.chdir(tmp_path)
    options = Options("linux", command_line_arguments=args)

    python_configurations = cibuildwheel.linux.get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    build_steps = list(cibuildwheel.linux.get_build_steps(options, python_configurations))

    # helper functions to extract test info
    def identifiers(step):
        return [c.identifier for c in step.platform_configs]

    def before_alls(step):
        return [options.build_options(c.identifier).before_all for c in step.platform_configs]

    pprint(build_steps)

    assert build_steps[0].container_image == "normal_container_image"
    assert identifiers(build_steps[0]) == ["cp36-manylinux_x86_64", "cp37-manylinux_x86_64"]
    assert before_alls(build_steps[0]) == ["", ""]

    assert build_steps[1].container_image == "other_container_image"
    assert identifiers(build_steps[1]) == ["cp38-manylinux_x86_64", "cp310-manylinux_x86_64"]
    assert before_alls(build_steps[1]) == ["", ""]

    assert build_steps[2].container_image == "other_container_image"
    assert identifiers(build_steps[2]) == ["cp39-manylinux_x86_64"]
    assert before_alls(build_steps[2]) == ["echo 'a cp39-only command'"]
