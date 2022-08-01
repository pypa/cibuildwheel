"""
These are utilities for the `/bin` scripts, not for the `cibuildwheel` program.
"""

from __future__ import annotations

from io import StringIO

from .typing import Protocol

__all__ = ("Printable", "dump_python_configurations")


class Printable(Protocol):
    def __str__(self) -> str:
        ...


def dump_python_configurations(inp: dict[str, dict[str, list[dict[str, Printable]]]]) -> str:
    output = StringIO()
    for header, values in inp.items():
        output.write(f"[{header}]\n")
        for inner_header, listing in values.items():
            output.write(f"{inner_header} = [\n")
            for item in listing:
                output.write("  { ")
                dict_contents = (f'{key} = "{value}"' for key, value in item.items())
                output.write(", ".join(dict_contents))
                output.write(" },\n")
            output.write("]\n")
        output.write("\n")
    # Strip the final newline, to avoid two blank lines at the end.
    return output.getvalue()[:-1]
