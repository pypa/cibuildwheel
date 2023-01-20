from __future__ import annotations

import textwrap
from pathlib import PurePath

import pytest

from cibuildwheel.util import (
    find_compatible_wheel,
    fix_ansi_codes_for_github_actions,
    format_safe,
    prepare_command,
)


def test_format_safe():
    assert format_safe("{wheel}", wheel="filename.whl") == "filename.whl"
    assert format_safe("command #{wheel}", wheel="filename.whl") == "command {wheel}"
    assert format_safe("{command #{wheel}}", wheel="filename.whl") == "{command {wheel}}"

    # check unmatched brackets
    assert format_safe("{command {wheel}", wheel="filename.whl") == "{command filename.whl"

    # check positional-style arguments i.e. {}
    assert (
        format_safe("find . -name  * -exec ls -a {} \\;", project="/project")
        == "find . -name  * -exec ls -a {} \\;"
    )

    assert format_safe("{param} {param}", param="1") == "1 1"
    assert format_safe("# {param} {param}", param="1") == "# 1 1"
    assert format_safe("#{not_a_param} {param}", param="1") == "#{not_a_param} 1"


def test_prepare_command():
    assert prepare_command("python -m {project}", project="project") == "python -m project"
    assert prepare_command("python -m {something}", project="project") == "python -m {something}"
    assert (
        prepare_command("python -m {something.abc}", project="project")
        == "python -m {something.abc}"
    )

    assert (
        prepare_command("python -m {something.abc[4]:3f}", project="project")
        == "python -m {something.abc[4]:3f}"
    )

    # test backslashes in the replacement
    assert (
        prepare_command(
            "command {wheel} \\Users\\Temp\\output_dir", wheel="\\Temporary Files\\cibw"
        )
        == "command \\Temporary Files\\cibw \\Users\\Temp\\output_dir"
    )

    # test some unusual syntax that used to trip up the str.format approach
    assert (
        prepare_command("{a}{a,b}{b:.2e}{c}{d%s}{e:3}{f[0]}", a="42", b="3.14159")
        == "42{a,b}{b:.2e}{c}{d%s}{e:3}{f[0]}"
    )


@pytest.mark.parametrize(
    ("wheel", "identifier"),
    [
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-cp38-abi3-macosx_11_0_x86_64.whl", "cp310-macosx_x86_64"),
        ("foo-0.1-cp38-abi3-manylinux2014_x86_64.whl", "cp310-manylinux_x86_64"),
        ("foo-0.1-cp38-abi3-musllinux_1_1_x86_64.whl", "cp310-musllinux_x86_64"),
        ("foo-0.1-py2.py3-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py2.py3-none-win_amd64.whl", "pp310-win_amd64"),
        ("foo-0.1-py3-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "pp310-win_amd64"),
    ],
)
def test_find_compatible_wheel_found(wheel: str, identifier: str):
    wheel_ = PurePath(wheel)
    found = find_compatible_wheel([wheel_], identifier)
    assert found is wheel_


@pytest.mark.parametrize(
    ("wheel", "identifier"),
    [
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp310-win32"),
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp37-win_amd64"),
        ("foo-0.1-cp38-abi3-macosx_11_0_x86_64.whl", "cp310-macosx_universal2"),
        ("foo-0.1-cp38-abi3-manylinux2014_x86_64.whl", "cp310-musllinux_x86_64"),
        ("foo-0.1-cp38-abi3-musllinux_1_1_x86_64.whl", "cp310-manylinux_x86_64"),
        ("foo-0.1-py2-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "cp37-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "pp37-win_amd64"),
        ("foo-0.1-cp38-cp38-win_amd64.whl", "cp310-win_amd64"),
    ],
)
def test_find_compatible_wheel_not_found(wheel: str, identifier: str):
    assert find_compatible_wheel([PurePath(wheel)], identifier) is None


def test_fix_ansi_codes_for_github_actions():
    input = textwrap.dedent(
        """
        This line is normal
        \033[1mThis line is bold
        This line is also bold
        \033[31m this line is red and bold
        This line is red and bold, too\033[0m
        This line is normal again
        """
    )

    expected = textwrap.dedent(
        """
        This line is normal
        \033[1mThis line is bold
        \033[1mThis line is also bold
        \033[1m\033[31m this line is red and bold
        \033[1m\033[31mThis line is red and bold, too\033[0m
        This line is normal again
        """
    )

    output = fix_ansi_codes_for_github_actions(input)

    assert output == expected
