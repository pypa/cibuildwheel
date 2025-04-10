import textwrap
from pathlib import Path
from pprint import pprint

import pytest

import cibuildwheel.platforms.linux
from cibuildwheel.oci_container import OCIContainerEngineConfig
from cibuildwheel.options import CommandLineArguments, Options


def test_linux_container_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Tests splitting linux builds by container image, container engine, and before_all
    """

    args = CommandLineArguments.defaults()
    args.platform = "linux"

    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
                [tool.cibuildwheel]
                manylinux-x86_64-image = "normal_container_image"
                manylinux-i686-image = "normal_container_image"
                build = "*-manylinux_x86_64"
                skip = "[gp]p*"
                archs = "x86_64 i686"

                [[tool.cibuildwheel.overrides]]
                select = "cp{38,39,310}-*"
                manylinux-x86_64-image = "other_container_image"
                manylinux-i686-image = "other_container_image"

                [[tool.cibuildwheel.overrides]]
                select = "cp39-*"
                before-all = "echo 'a cp39-only command'"

                [[tool.cibuildwheel.overrides]]
                select = "cp310-*"
                container-engine = "docker; create_args: --privileged"
            """
        )
    )

    monkeypatch.chdir(tmp_path)
    options = Options("linux", command_line_arguments=args, env={})

    python_configurations = cibuildwheel.platforms.linux.get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    build_steps = list(cibuildwheel.platforms.linux.get_build_steps(options, python_configurations))

    # helper functions to extract test info
    def identifiers(step: cibuildwheel.platforms.linux.BuildStep) -> list[str]:
        return [c.identifier for c in step.platform_configs]

    def before_alls(step: cibuildwheel.platforms.linux.BuildStep) -> list[str]:
        return [options.build_options(c.identifier).before_all for c in step.platform_configs]

    def container_engines(
        step: cibuildwheel.platforms.linux.BuildStep,
    ) -> list[OCIContainerEngineConfig]:
        return [options.build_options(c.identifier).container_engine for c in step.platform_configs]

    pprint(build_steps)

    default_container_engine = OCIContainerEngineConfig(name="docker")

    assert build_steps[0].container_image == "other_container_image"
    assert identifiers(build_steps[0]) == ["cp38-manylinux_x86_64"]
    assert before_alls(build_steps[0]) == [""]
    assert container_engines(build_steps[0]) == [default_container_engine]

    assert build_steps[1].container_image == "other_container_image"
    assert identifiers(build_steps[1]) == ["cp39-manylinux_x86_64"]
    assert before_alls(build_steps[1]) == ["echo 'a cp39-only command'"]
    assert container_engines(build_steps[1]) == [default_container_engine]

    assert build_steps[2].container_image == "other_container_image"
    assert identifiers(build_steps[2]) == ["cp310-manylinux_x86_64"]
    assert before_alls(build_steps[2]) == [""]
    assert container_engines(build_steps[2]) == [
        OCIContainerEngineConfig(name="docker", create_args=("--privileged",))
    ]

    assert build_steps[3].container_image == "normal_container_image"
    assert identifiers(build_steps[3]) == [
        "cp311-manylinux_x86_64",
        "cp312-manylinux_x86_64",
        "cp313-manylinux_x86_64",
    ]
    assert before_alls(build_steps[3]) == [""] * 3
    assert container_engines(build_steps[3]) == [default_container_engine] * 3
