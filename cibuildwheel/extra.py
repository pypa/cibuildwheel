"""
These are utilities for the `/bin` scripts, not for the `cibuildwheel` program.
"""

from typing import Any, Dict

import toml.encoder
from packaging.version import Version


class InlineArrayDictEncoder(toml.encoder.TomlEncoder):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.dump_funcs[Version] = lambda v: f'"{v}"'

    def dump_sections(self, o: Dict[str, Any], sup: str) -> Any:
        if not all(isinstance(a, list) for a in o.values()):
            return super().dump_sections(o, sup)
        val = ""
        for k, v in o.items():
            inner = ",\n  ".join(self.dump_inline_table(d_i).strip() for d_i in v)
            val += f"{k} = [\n  {inner},\n]\n"
        return val, self._dict()
