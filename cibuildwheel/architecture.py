import platform as platform_module
import re
import shutil
import subprocess
import sys
import typing
from collections.abc import Set
from enum import StrEnum, auto
from typing import Final, Literal, Self

from cibuildwheel import errors
from cibuildwheel.typing import PlatformName

PRETTY_NAMES: Final[dict[PlatformName, str]] = {
    "linux": "Linux",
    "macos": "macOS",
    "windows": "Windows",
    "pyodide": "Pyodide",
    "android": "Android",
    "ios": "iOS",
}

ARCH_SYNONYMS: Final[list[dict[PlatformName, str | None]]] = [
    {"linux": "x86_64", "macos": "x86_64", "windows": "AMD64", "android": "x86_64"},
    {"linux": "i686", "macos": None, "windows": "x86"},
    {"linux": "aarch64", "macos": "arm64", "windows": "ARM64", "android": "arm64_v8a"},
]


def arch_synonym(arch: str, from_platform: PlatformName, to_platform: PlatformName) -> str | None:
    for arch_synonym_ in ARCH_SYNONYMS:
        if arch == arch_synonym_.get(from_platform):
            return arch_synonym_.get(to_platform, arch)

    return arch


def _check_aarch32_el0() -> bool:
    """Check if running armv7l natively on aarch64 is supported"""
    if not sys.platform.startswith("linux"):
        return False
    if platform_module.machine() != "aarch64":
        return False
    executable = shutil.which("linux32")
    if executable is None:
        return False
    check = subprocess.run([executable, "uname", "-m"], check=False, capture_output=True, text=True)
    return check.returncode == 0 and check.stdout.startswith("armv")


@typing.final
class Architecture(StrEnum):
    # mac/linux/android archs
    x86_64 = auto()

    # linux archs
    i686 = auto()
    aarch64 = auto()
    ppc64le = auto()
    s390x = auto()
    armv7l = auto()
    riscv64 = auto()

    # mac archs
    universal2 = auto()
    arm64 = auto()

    # windows archs
    x86 = auto()
    AMD64 = "AMD64"
    ARM64 = "ARM64"

    # WebAssembly
    wasm32 = auto()

    # android archs
    arm64_v8a = auto()

    # iOS "multiarch" architectures that include both
    # the CPU architecture and the ABI.
    arm64_iphoneos = auto()
    arm64_iphonesimulator = auto()
    x86_64_iphonesimulator = auto()

    @classmethod
    def parse_config(cls, config: str, platform: PlatformName) -> set[Self]:
        result = set()
        for arch_str in re.split(r"[\s,]+", config):
            match arch_str:
                case "auto":
                    result |= cls.auto_archs(platform=platform)
                case "native":
                    if native_arch := cls.native_arch(platform=platform):
                        result.add(native_arch)
                case "all":
                    result |= cls.all_archs(platform=platform)
                case "auto64":
                    result |= cls.bitness_archs(platform=platform, bitness="64")
                case "auto32":
                    result |= cls.bitness_archs(platform=platform, bitness="32")
                case _:
                    try:
                        result.add(cls(arch_str))
                    except ValueError as e:
                        msg = f"Invalid architecture '{arch_str}'"
                        raise errors.ConfigurationError(msg) from e
        return result

    @classmethod
    def native_arch(cls, platform: PlatformName) -> Self | None:
        native_machine = platform_module.machine()
        native_architecture = cls(native_machine)

        # Cross-platform support. Used for --print-build-identifiers or docker builds.
        host_platform: PlatformName = (
            "windows"
            if sys.platform.startswith("win")
            else ("macos" if sys.platform.startswith("darwin") else "linux")
        )

        if platform == "pyodide":
            return cls.wasm32
        elif platform == "ios":
            # Can only build for iOS on macOS. The "native" architecture is the
            # simulator for the macOS native platform.
            if host_platform == "macos":
                if native_architecture == cls.x86_64:
                    return cls.x86_64_iphonesimulator
                else:
                    return cls.arm64_iphonesimulator
            else:
                return None

        # we might need to rename the native arch to the machine we're running
        # on, as the same arch can have different names on different platforms
        if host_platform != platform:
            synonym = arch_synonym(native_machine, host_platform, platform)
            if synonym is None:
                # can't build anything on this platform
                return None

            native_architecture = cls(synonym)

        return native_architecture

    @classmethod
    def auto_archs(cls, platform: PlatformName) -> set[Self]:
        native_arch = cls.native_arch(platform)
        if native_arch is None:
            return set()  # can't build anything on this platform
        result = {native_arch}

        match platform:
            case "windows" if cls.AMD64 in result:
                result.add(cls.x86)
            case "ios" if native_arch == cls.arm64_iphonesimulator:
                # Also build the device wheel if we're on ARM64.
                result.add(cls.arm64_iphoneos)

        return result

    @classmethod
    def all_archs(cls, platform: PlatformName) -> set[Self]:
        all_archs_map = {
            "linux": {
                cls.x86_64,
                cls.i686,
                cls.aarch64,
                cls.ppc64le,
                cls.s390x,
                cls.armv7l,
                cls.riscv64,
            },
            "macos": {cls.x86_64, cls.arm64, cls.universal2},
            "windows": {cls.x86, cls.AMD64, cls.ARM64},
            "pyodide": {cls.wasm32},
            "android": {cls.x86_64, cls.arm64_v8a},
            "ios": {
                cls.x86_64_iphonesimulator,
                cls.arm64_iphonesimulator,
                cls.arm64_iphoneos,
            },
        }
        return all_archs_map[platform]

    @classmethod
    def bitness_archs(cls, platform: PlatformName, bitness: Literal["64", "32"]) -> set[Self]:
        # This map maps 64-bit architectures to their 32-bit equivalents.
        archs_map = {
            cls.x86_64: cls.i686,
            cls.AMD64: cls.x86,
            cls.aarch64: cls.armv7l,
        }
        native_arch = cls.native_arch(platform)

        if native_arch is None:
            return set()  # can't build anything on this platform

        if native_arch == cls.wasm32:
            return {native_arch} if bitness == "32" else set()

        match bitness:
            case "64":
                return {native_arch} if native_arch not in archs_map.values() else set()
            case "32":
                if native_arch in archs_map.values():
                    return {native_arch}
                elif native_arch in archs_map and platform in {"linux", "windows"}:
                    if native_arch == cls.aarch64 and not _check_aarch32_el0():
                        # If we're on aarch64, skip if we cannot build armv7l wheels.
                        return set()
                    return {archs_map[native_arch]}
                else:
                    return set()
            case _:
                typing.assert_never(bitness)


def allowed_architectures_check(
    platform: PlatformName,
    architectures: Set[Architecture],
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
