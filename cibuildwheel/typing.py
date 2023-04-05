from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Union

if sys.version_info < (3, 8):
    from typing_extensions import Final, Literal, OrderedDict, Protocol, TypedDict
else:
    from typing import Final, Literal, OrderedDict, Protocol, TypedDict

if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, assert_never
else:
    from typing import NotRequired, assert_never

__all__ = (
    "Final",
    "Literal",
    "PLATFORMS",
    "PathOrStr",
    "PlatformName",
    "Protocol",
    "PLATFORMS",
    "PopenBytes",
    "Protocol",
    "TypedDict",
    "OrderedDict",
    "assert_never",
    "NotRequired",
)


if TYPE_CHECKING:
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
