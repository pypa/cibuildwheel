from __future__ import annotations

import functools
import platform as platform_module
import re
import sys
from enum import Enum

from .typing import Final, Literal, PlatformName, assert_never

PRETTY_NAMES: Final = {"linux": "Linux", "macos": "macOS", "windows": "Windows"}

ARCH_CATEGORIES: Final[dict[str, set[str]]] = {
    "32": {"i686", "x86"},
    "64": {"x86_64", "AMD64"},
    "arm": {"ARM64", "aarch64", "arm64"},
}

PLATFORM_CATEGORIES: Final[dict[PlatformName, set[str]]] = {
    "linux": {"i686", "x86_64", "aarch64", "ppc64le", "s390x"},
    "macos": {"x86_64", "arm64", "universal2"},
    "windows": {"x86", "AMD64", "ARM64"},
}


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
        host_platform = (
            "windows"
            if sys.platform.startswith("win")
            else ("macos" if sys.platform.startswith("darwin") else "linux")
        )

        result = set()

        # Replace native_machine with the matching machine for intel or arm
        if host_platform == platform:
            native_architecture = Architecture(native_machine)
            result.add(native_architecture)
        else:
            for arch_group in ARCH_CATEGORIES.values():
                if native_machine in arch_group:
                    possible_archs = arch_group & PLATFORM_CATEGORIES[platform]
                    if len(possible_archs) == 1:
                        (cross_machine,) = possible_archs
                        result.add(Architecture(cross_machine))

        if platform == "linux" and Architecture.x86_64 in result:
            # x86_64 machines can run i686 containers
            result.add(Architecture.i686)

        if platform == "windows" and Architecture.AMD64 in result:
            result.add(Architecture.x86)

        return result

    @staticmethod
    def all_archs(platform: PlatformName) -> set[Architecture]:
        all_archs_map = {
            "linux": {Architecture[item] for item in PLATFORM_CATEGORIES["linux"]},
            "macos": {Architecture[item] for item in PLATFORM_CATEGORIES["macos"]},
            "windows": {Architecture[item] for item in PLATFORM_CATEGORIES["windows"]},
        }
        return all_archs_map[platform]

    @staticmethod
    def bitness_archs(platform: PlatformName, bitness: Literal["64", "32"]) -> set[Architecture]:
        archs_32 = {Architecture[item] for item in ARCH_CATEGORIES["32"]}
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
