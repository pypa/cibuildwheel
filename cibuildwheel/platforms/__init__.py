from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final, Protocol

from cibuildwheel import errors
from cibuildwheel.platforms import android, ios, linux, macos, pyodide, windows

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from cibuildwheel.architecture import Architecture
    from cibuildwheel.options import Options
    from cibuildwheel.selector import BuildSelector
    from cibuildwheel.typing import GenericPythonConfiguration, PlatformName


class PlatformModule(Protocol):
    # note that as per PEP544, the self argument is ignored when the protocol
    # is applied to a module
    def all_python_configurations(self) -> Sequence[GenericPythonConfiguration]: ...

    def get_python_configurations(
        self, build_selector: BuildSelector, architectures: set[Architecture]
    ) -> Sequence[GenericPythonConfiguration]: ...

    def build(self, options: Options, tmp_path: Path) -> None: ...


ALL_PLATFORM_MODULES: Final[dict[PlatformName, PlatformModule]] = {
    "linux": linux,
    "windows": windows,
    "macos": macos,
    "pyodide": pyodide,
    "android": android,
    "ios": ios,
}


def native_platform() -> PlatformName:
    if sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    else:
        msg = (
            'Unable to detect platform from "sys.platform". cibuildwheel doesn\'t '
            "support building wheels for this platform. You might be able to build for a different "
            "platform using the --platform argument. Check --help output for more information."
        )
        raise errors.ConfigurationError(msg)


def get_build_identifiers(
    platform_module: PlatformModule,
    build_selector: BuildSelector,
    architectures: set[Architecture],
) -> list[str]:
    python_configurations = platform_module.get_python_configurations(build_selector, architectures)
    return [config.identifier for config in python_configurations]
