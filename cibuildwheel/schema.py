from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DIR = Path(__file__).parent.resolve()


def get_schema(tool_name: str = "cibuildwheel") -> dict[str, Any]:
    "Get the stored complete schema for cibuildwheel settings."
    assert tool_name == "cibuildwheel", "Only cibuildwheel is supported."

    with DIR.joinpath("resources/cibuildwheel.schema.json").open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]
