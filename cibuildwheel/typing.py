from __future__ import annotations

import os
import subprocess
import typing
from typing import Final, Literal, Protocol, Union

__all__ = (
    "PLATFORMS",
    "PathOrStr",
    "PlatformName",
    "PLATFORMS",
    "PopenBytes",
)


if typing.TYPE_CHECKING:
    PopenBytes = subprocess.Popen[bytes]
    PathOrStr = Union[str, os.PathLike[str]]
else:
    PopenBytes = subprocess.Popen
    PathOrStr = Union[str, "os.PathLike[str]"]


PlatformName = Literal["linux", "macos", "windows"]
PLATFORMS: Final[set[PlatformName]] = {"linux", "macos", "windows"}


class GenericPythonConfiguration(Protocol):
    @property
    def identifier(self) -> str:
        ...
