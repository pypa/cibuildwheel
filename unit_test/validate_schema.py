from pathlib import Path

import pytest

from cibuildwheel._compat import tomllib

api = pytest.importorskip("validate_pyproject.api")

DIR = Path(__file__).parent.resolve()


def test_validate_default_schema():
    filepath = DIR.parent / "cibuildwheel/resources/defaults.toml"
    with filepath.open("rb") as f:
        example = tomllib.load(f)

    validator = api.Validator()
    assert validator(example) is not None
