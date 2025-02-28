from __future__ import annotations

import os
import typing
from typing import Final, Literal, Protocol

__all__ = (
    "PLATFORMS",
    "PathOrStr",
    "PlatformName",
)


PathOrStr = str | os.PathLike[str]


PlatformName = Literal["linux", "macos", "windows", "pyodide"]
PLATFORMS: Final[frozenset[PlatformName]] = frozenset(typing.get_args(PlatformName))


class GenericPythonConfiguration(Protocol):
    @property
    def identifier(self) -> str: ...
