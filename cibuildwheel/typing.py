import os
import subprocess
import sys
from typing import TYPE_CHECKING, NoReturn, Set, Union

if sys.version_info < (3, 8):
    from typing_extensions import Final, Literal, TypedDict
else:
    from typing import Final, Literal, TypedDict


__all__ = (
    "Final",
    "Literal",
    "TypedDict",
    "Set",
    "Union",
    "PopenBytes",
    "PathOrStr",
    "PlatformName",
    "PLATFORMS",
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
