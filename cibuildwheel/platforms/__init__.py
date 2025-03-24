from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final, Protocol

from cibuildwheel.architecture import Architecture
from cibuildwheel.options import Options
from cibuildwheel.platforms import ios, linux, macos, pyodide, windows
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
    "ios": ios,
}


def get_build_identifiers(
    platform_module: PlatformModule,
    build_selector: BuildSelector,
    architectures: set[Architecture],
) -> list[str]:
    python_configurations = platform_module.get_python_configurations(build_selector, architectures)
    return [config.identifier for config in python_configurations]
