from __future__ import annotations

import re
from pathlib import Path

import pytest
import validate_pyproject.api

from cibuildwheel._compat import tomllib

DIR = Path(__file__).parent.resolve()


def test_validate_default_schema():
    filepath = DIR.parent / "cibuildwheel/resources/defaults.toml"
    with filepath.open("rb") as f:
        example = tomllib.load(f)

    validator = validate_pyproject.api.Validator()
    assert validator(example) is not None


def test_validate_container_engine():
    """
    This test checks container engine can be overridden - it used to be a
    global option but is now a build option.
    """

    example = tomllib.loads(
        """
        [tool.cibuildwheel]
        container-engine = "docker"

        [tool.cibuildwheel.linux]
        container-engine = "docker"

        [[tool.cibuildwheel.overrides]]
        select = "*_x86_64"
        container-engine = "docker; create_args: --platform linux/arm64/v8"
        """
    )

    validator = validate_pyproject.api.Validator()
    assert validator(example) is not None


@pytest.mark.parametrize("platform", ["macos", "windows"])
def test_validate_bad_container_engine(platform: str) -> None:
    """
    container-engine is not a valid option for macos or windows
    """
    example = tomllib.loads(
        f"""
        [tool.cibuildwheel.{platform}]
        container-engine = "docker"
        """
    )

    validator = validate_pyproject.api.Validator()
    with pytest.raises(validate_pyproject.error_reporting.ValidationError):
        validator(example)


def test_overrides_select():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        select = "somestring"
        repair-wheel-command = "something"
        """
    )

    validator = validate_pyproject.api.Validator()
    assert validator(example) is not None


def test_overrides_no_select():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        repair-wheel-command = "something"
        """
    )

    validator = validate_pyproject.api.Validator()
    with pytest.raises(validate_pyproject.error_reporting.ValidationError):
        validator(example)


def test_overrides_only_select():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        select = "somestring"
        """
    )

    validator = validate_pyproject.api.Validator()
    with pytest.raises(validate_pyproject.error_reporting.ValidationError):
        validator(example)


def test_overrides_valid_inherit():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        inherit.repair-wheel-command = "append"
        select = "somestring"
        repair-wheel-command = ["something"]
        """
    )

    validator = validate_pyproject.api.Validator()
    assert validator(example) is not None


def test_overrides_invalid_inherit():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        inherit.something = "append"
        select = "somestring"
        repair-wheel-command = "something"
        """
    )

    validator = validate_pyproject.api.Validator()
    with pytest.raises(validate_pyproject.error_reporting.ValidationError):
        validator(example)


def test_overrides_invalid_inherit_value():
    example = tomllib.loads(
        """
        [[tool.cibuildwheel.overrides]]
        inherit.repair-wheel-command = "nothing"
        select = "somestring"
        repair-wheel-command = "something"
        """
    )

    validator = validate_pyproject.api.Validator()
    with pytest.raises(validate_pyproject.error_reporting.ValidationError):
        validator(example)


def test_docs_examples():
    """
    Parse out all the configuration examples, build valid TOML out of them, and
    make sure they pass.
    """

    expr = re.compile(
        r"""
!!! tab examples "pyproject.toml"
\s*
\s*```toml
(.*?)```""",
        re.MULTILINE | re.DOTALL,
    )

    txt = DIR.parent.joinpath("docs/options.md").read_text()

    blocks: list[str] = []
    for match in expr.finditer(txt):
        lines = (line.strip() for line in match.group(1).strip().splitlines() if line.strip())
        block: list[str] = []
        header = ""
        for line in lines:
            if line.startswith(("[tool.cibuildwheel", "[[tool.cibuildwheel")):
                header = line
            elif line.startswith("#"):
                if block:
                    blocks.append("\n".join([header, *block]))
                    block = []
            elif " = " in line and any(x.startswith(line.partition(" = ")[0]) for x in block):
                blocks.append("\n".join([header, *block]))
                block = [line]
            else:
                block.append(line)
        blocks.append("\n".join([header, *block]))

    for example_txt in blocks:
        print(example_txt)
        print()
        example = tomllib.loads(example_txt)
        validator = validate_pyproject.api.Validator()
        assert validator(example) is not None
