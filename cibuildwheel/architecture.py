from __future__ import annotations

import functools
import platform as platform_module
import re
import sys
from enum import Enum

from .typing import Final, Literal, PlatformName, assert_never

PRETTY_NAMES: Final = {"linux": "Linux", "macos": "macOS", "windows": "Windows"}

ARCH_SYNONYMS: Final[list[dict[PlatformName, str | None]]] = [
    {"linux": "x86_64", "macos": "x86_64", "windows": "AMD64"},
    {"linux": "i686", "macos": None, "windows": "x86"},
    {"linux": "aarch64", "macos": "arm64", "windows": "ARM64"},
]


@functools.total_ordering
class Architecture(Enum):
    value: str

    # mac/linux archs
    x86_64 = "x86_64"

    # linux archs
    i686 = "i686"
    aarch64 = "aarch64"
    ppc64le = "ppc64le"
    s390x = "s390x"

    # mac archs
    universal2 = "universal2"
    arm64 = "arm64"

    # windows archs
    x86 = "x86"
    AMD64 = "AMD64"
    ARM64 = "ARM64"

    # Allow this to be sorted
    def __lt__(self, other: Architecture) -> bool:
        return self.value < other.value

    @staticmethod
    def parse_config(config: str, platform: PlatformName) -> set[Architecture]:
        result = set()
        for arch_str in re.split(r"[\s,]+", config):
            if arch_str == "auto":
                result |= Architecture.auto_archs(platform=platform)
            elif arch_str == "native":
                result.add(Architecture(platform_module.machine()))
            elif arch_str == "all":
                result |= Architecture.all_archs(platform=platform)
            elif arch_str == "auto64":
                result |= Architecture.bitness_archs(platform=platform, bitness="64")
            elif arch_str == "auto32":
                result |= Architecture.bitness_archs(platform=platform, bitness="32")
            else:
                result.add(Architecture(arch_str))
        return result

    @staticmethod
    def auto_archs(platform: PlatformName) -> set[Architecture]:
        native_machine = platform_module.machine()

        # Cross-platform support. Used for --print-build-identifiers or docker builds.
        host_platform: PlatformName = (
            "windows"
            if sys.platform.startswith("win")
            else ("macos" if sys.platform.startswith("darwin") else "linux")
        )

        native_architecture = Architecture(native_machine)

        # we might need to rename the native arch to the machine we're running
        # on, as the same arch can have different names on different platforms
        if host_platform != platform:
            for arch_synonym in ARCH_SYNONYMS:
                if native_machine == arch_synonym.get(host_platform):
                    synonym = arch_synonym[platform]

                    if synonym is None:
                        # can't build anything on this platform
                        return set()

                    native_architecture = Architecture(synonym)

        result = {native_architecture}

        if platform == "linux" and Architecture.x86_64 in result:
            # x86_64 machines can run i686 containers
            result.add(Architecture.i686)

        if platform == "windows" and Architecture.AMD64 in result:
            result.add(Architecture.x86)

        return result

    @staticmethod
    def all_archs(platform: PlatformName) -> set[Architecture]:
        all_archs_map = {
            "linux": {
                Architecture.x86_64,
                Architecture.i686,
                Architecture.aarch64,
                Architecture.ppc64le,
                Architecture.s390x,
            },
            "macos": {Architecture.x86_64, Architecture.arm64, Architecture.universal2},
            "windows": {Architecture.x86, Architecture.AMD64, Architecture.ARM64},
        }
        return all_archs_map[platform]

    @staticmethod
    def bitness_archs(platform: PlatformName, bitness: Literal["64", "32"]) -> set[Architecture]:
        archs_32 = {Architecture.i686, Architecture.x86}
        auto_archs = Architecture.auto_archs(platform)

        if bitness == "64":
            return auto_archs - archs_32
        elif bitness == "32":
            return auto_archs & archs_32
        else:
            assert_never(bitness)


def allowed_architectures_check(
    platform: PlatformName,
    architectures: set[Architecture],
) -> None:

    allowed_architectures = Architecture.all_archs(platform)

    msg = f"{PRETTY_NAMES[platform]} only supports {sorted(allowed_architectures)} at the moment."

    if platform != "linux":
        msg += " If you want to set emulation architectures on Linux, use CIBW_ARCHS_LINUX instead."

    if not architectures <= allowed_architectures:
        msg = f"Invalid archs option {architectures}. " + msg
        raise ValueError(msg)

    if not architectures:
        msg = "Empty archs option set. " + msg
        raise ValueError(msg)
