import platform as platform_module
import re
import shutil
import subprocess
import sys
import typing
from collections.abc import Set
from enum import StrEnum, auto
from typing import Final, Literal

from cibuildwheel import errors

from .typing import PlatformName

PRETTY_NAMES: Final[dict[PlatformName, str]] = {
    "linux": "Linux",
    "macos": "macOS",
    "windows": "Windows",
    "pyodide": "Pyodide",
    "ios": "iOS",
}

ARCH_SYNONYMS: Final[list[dict[PlatformName, str | None]]] = [
    {"linux": "x86_64", "macos": "x86_64", "windows": "AMD64"},
    {"linux": "i686", "macos": None, "windows": "x86"},
    {"linux": "aarch64", "macos": "arm64", "windows": "ARM64"},
]


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
    # mac/linux archs
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

    # iOS "multiarch" architectures that include both
    # the CPU architecture and the ABI.
    arm64_iphoneos = auto()
    arm64_iphonesimulator = auto()
    x86_64_iphonesimulator = auto()

    @staticmethod
    def parse_config(config: str, platform: PlatformName) -> "set[Architecture]":
        result = set()
        for arch_str in re.split(r"[\s,]+", config):
            if arch_str == "auto":
                result |= Architecture.auto_archs(platform=platform)
            elif arch_str == "native":
                native_arch = Architecture.native_arch(platform=platform)
                if native_arch:
                    result.add(native_arch)
            elif arch_str == "all":
                result |= Architecture.all_archs(platform=platform)
            elif arch_str == "auto64":
                result |= Architecture.bitness_archs(platform=platform, bitness="64")
            elif arch_str == "auto32":
                result |= Architecture.bitness_archs(platform=platform, bitness="32")
            else:
                try:
                    result.add(Architecture(arch_str))
                except ValueError as e:
                    msg = f"Invalid architecture '{arch_str}'"
                    raise errors.ConfigurationError(msg) from e
        return result

    @staticmethod
    def native_arch(platform: PlatformName) -> "Architecture | None":
        native_machine = platform_module.machine()
        native_architecture = Architecture(native_machine)

        # Cross-platform support. Used for --print-build-identifiers or docker builds.
        host_platform: PlatformName = (
            "windows"
            if sys.platform.startswith("win")
            else ("macos" if sys.platform.startswith("darwin") else "linux")
        )

        if platform == "pyodide":
            return Architecture.wasm32
        elif platform == "ios":
            # Can only build for iOS on macOS. The "native" architecture is the
            # simulator for the macOS native platform.
            if host_platform == "macos":
                if native_architecture == Architecture.x86_64:
                    return Architecture.x86_64_iphonesimulator
                else:
                    return Architecture.arm64_iphonesimulator
            else:
                return None

        # we might need to rename the native arch to the machine we're running
        # on, as the same arch can have different names on different platforms
        if host_platform != platform:
            for arch_synonym in ARCH_SYNONYMS:
                if native_machine == arch_synonym.get(host_platform):
                    synonym = arch_synonym[platform]

                    if synonym is None:
                        # can't build anything on this platform
                        return None

                    native_architecture = Architecture(synonym)

        return native_architecture

    @staticmethod
    def auto_archs(platform: PlatformName) -> "set[Architecture]":
        native_arch = Architecture.native_arch(platform)
        if native_arch is None:
            return set()  # can't build anything on this platform
        result = {native_arch}

        if platform == "linux":
            if Architecture.x86_64 in result:
                # x86_64 machines can run i686 containers
                result.add(Architecture.i686)
            elif Architecture.aarch64 in result and _check_aarch32_el0():
                result.add(Architecture.armv7l)

        elif platform == "windows" and Architecture.AMD64 in result:
            result.add(Architecture.x86)

        elif platform == "ios" and native_arch == Architecture.arm64_iphonesimulator:
            # Also build the device wheel if we're on ARM64.
            result.add(Architecture.arm64_iphoneos)

        return result

    @staticmethod
    def all_archs(platform: PlatformName) -> "set[Architecture]":
        all_archs_map = {
            "linux": {
                Architecture.x86_64,
                Architecture.i686,
                Architecture.aarch64,
                Architecture.ppc64le,
                Architecture.s390x,
                Architecture.armv7l,
                Architecture.riscv64,
            },
            "macos": {Architecture.x86_64, Architecture.arm64, Architecture.universal2},
            "windows": {Architecture.x86, Architecture.AMD64, Architecture.ARM64},
            "pyodide": {Architecture.wasm32},
            "ios": {
                Architecture.x86_64_iphonesimulator,
                Architecture.arm64_iphonesimulator,
                Architecture.arm64_iphoneos,
            },
        }
        return all_archs_map[platform]

    @staticmethod
    def bitness_archs(platform: PlatformName, bitness: Literal["64", "32"]) -> "set[Architecture]":
        archs_32 = {Architecture.i686, Architecture.x86, Architecture.armv7l}
        auto_archs = Architecture.auto_archs(platform)

        if bitness == "64":
            return auto_archs - archs_32
        if bitness == "32":
            return auto_archs & archs_32
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
