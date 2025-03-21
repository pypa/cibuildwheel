import json
from typing import Any

from .util import resources


def get_schema(tool_name: str = "cibuildwheel") -> dict[str, Any]:
    "Get the stored complete schema for cibuildwheel settings."
    assert tool_name == "cibuildwheel", "Only cibuildwheel is supported."

    with resources.CIBUILDWHEEL_SCHEMA.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]
