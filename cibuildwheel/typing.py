from __future__ import annotations

import os
import subprocess
import typing
from typing import Final, Literal, Protocol, Union

__all__ = (
    "PLATFORMS",
    "PathOrStr",
    "PlatformName",
    "PopenBytes",
)


if typing.TYPE_CHECKING:
    PopenBytes = subprocess.Popen[bytes]
    PathOrStr = str | os.PathLike[str]
else:
    PopenBytes = subprocess.Popen
    PathOrStr = Union[str, "os.PathLike[str]"]


PlatformName = Literal[
    "linux",
    "macos",
    "windows",
    "pyodide",
    "ios",
    "iphoneos",
    "iphonesimulator",
]
PLATFORMS: Final[set[PlatformName]] = {
    "linux",
    "macos",
    "windows",
    "pyodide",
    "ios",
    "iphoneos",
    "iphonesimulator",
}


class GenericPythonConfiguration(Protocol):
    @property
    def identifier(self) -> str: ...
