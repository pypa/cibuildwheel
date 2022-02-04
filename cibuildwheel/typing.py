import os
import subprocess
import sys
from typing import TYPE_CHECKING, NoReturn, Set, Union

if sys.version_info < (3, 8):
    from typing_extensions import Final, Literal, OrderedDict, Protocol, TypedDict
else:
    from typing import Final, Literal, OrderedDict, Protocol, TypedDict


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
    "Set",
    "TypedDict",
    "OrderedDict",
    "Union",
    "assert_never",
)


if TYPE_CHECKING:
    PopenBytes = subprocess.Popen[bytes]
    PathOrStr = Union[str, os.PathLike[str]]
else:
    PopenBytes = subprocess.Popen
    PathOrStr = Union[str, "os.PathLike[str]"]


PlatformName = Literal["linux", "macos", "windows"]
PLATFORMS: Final[Set[PlatformName]] = {"linux", "macos", "windows"}


def assert_never(value: NoReturn) -> NoReturn:
    assert False, f"Unhandled value: {value} ({type(value).__name__})"  # noqa: B011
