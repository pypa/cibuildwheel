import os
import typing
from typing import Final, Literal, Protocol, TypeVar

__all__ = (
    "PLATFORMS",
    "PathOrStr",
    "PlatformName",
)


PathOrStr = str | os.PathLike[str]
PathT = TypeVar("PathT", bound=os.PathLike[str])

PlatformName = Literal["linux", "macos", "windows", "pyodide", "android", "ios"]
PLATFORMS: Final[frozenset[PlatformName]] = frozenset(typing.get_args(PlatformName))


class GenericPythonConfiguration(Protocol):
    @property
    def identifier(self) -> str: ...
