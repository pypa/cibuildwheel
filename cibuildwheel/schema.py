from __future__ import annotations

__lazy_modules__ = ["cibuildwheel.util", "json"]

import json

from cibuildwheel.util import resources

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any


def get_schema(tool_name: str = "cibuildwheel") -> dict[str, Any]:
    "Get the stored complete schema for cibuildwheel settings."
    assert tool_name == "cibuildwheel", "Only cibuildwheel is supported."

    with resources.CIBUILDWHEEL_SCHEMA.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]
