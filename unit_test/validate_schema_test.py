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


def test_validate_bad_container_engine():
    example = tomllib.loads(
        """
        [tool.cibuildwheel.linux]
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
