import functools
import platform as platform_module
import re
from enum import Enum
from typing import Set

from .typing import Literal, PlatformName, assert_never

PRETTY_NAMES = {'linux': 'Linux', 'macos': 'macOS', 'windows': 'Windows'}


@functools.total_ordering
class Architecture(Enum):
    value: str

    # mac/linux archs
    x86_64 = 'x86_64'

    # linux archs
    i686 = 'i686'
    aarch64 = 'aarch64'
    ppc64le = 'ppc64le'
    s390x = 's390x'

    # mac archs
    universal2 = 'universal2'
    arm64 = 'arm64'

    # windows archs
    x86 = 'x86'
    AMD64 = 'AMD64'

    # Allow this to be sorted
    def __lt__(self, other: "Architecture") -> bool:
        return self.value < other.value

    @staticmethod
    def parse_config(config: str, platform: PlatformName) -> 'Set[Architecture]':
        result = set()
        for arch_str in re.split(r'[\s,]+', config):
            if arch_str == 'auto':
                result |= Architecture.auto_archs(platform=platform)
            elif arch_str == 'native':
                result.add(Architecture(platform_module.machine()))
            elif arch_str == 'all':
                result |= Architecture.all_archs(platform=platform)
            elif arch_str == 'auto64':
                result |= Architecture.bitiness_archs(platform=platform, bitiness="64")
            elif arch_str == 'auto32':
                result |= Architecture.bitiness_archs(platform=platform, bitiness="32")
            else:
                result.add(Architecture(arch_str))
        return result

    @staticmethod
    def auto_archs(platform: PlatformName) -> 'Set[Architecture]':
        native_architecture = Architecture(platform_module.machine())
        result = {native_architecture}

        if platform == 'linux' and native_architecture == Architecture.x86_64:
            # x86_64 machines can run i686 docker containers
            result.add(Architecture.i686)

        if platform == 'windows' and native_architecture == Architecture.AMD64:
            result.add(Architecture.x86)

        if platform == 'macos' and native_architecture == Architecture.arm64:
            # arm64 can build and test both archs of a universal2 wheel.
            result.add(Architecture.universal2)

        return result

    @staticmethod
    def all_archs(platform: PlatformName) -> 'Set[Architecture]':
        if platform == 'linux':
            return {Architecture.x86_64, Architecture.i686, Architecture.aarch64, Architecture.ppc64le, Architecture.s390x}
        elif platform == 'macos':
            return {Architecture.x86_64, Architecture.arm64, Architecture.universal2}
        elif platform == 'windows':
            return {Architecture.x86, Architecture.AMD64}
        else:
            assert_never(platform)

    @staticmethod
    def bitiness_archs(platform: PlatformName, bitiness: Literal["64", "32"]) -> 'Set[Architecture]':
        native_architecture = Architecture(platform_module.machine())

        if native_architecture in {Architecture.x86_64, Architecture.aarch64, Architecture.ppc64le, Architecture.s390x, Architecture.AMD64}:
            if bitiness == "64":
                return {native_architecture}
            else:
                if native_architecture == Architecture.x86_64 and platform != "macos":
                    return {Architecture.i686}
                elif native_architecture == Architecture.AMD64:
                    return {Architecture.x86}
                else:
                    return set()
        elif native_architecture in {Architecture.i686, Architecture.x86}:
            return {native_architecture} if bitiness == "32" else set()
        else:
            # assert_never doesn't work here, oddly, maybe due to set checking above
            raise RuntimeError("Cannot be reached")


def allowed_architectures_check(
    platform: PlatformName,
    architectures: Set[Architecture],
) -> None:

    allowed_architectures = Architecture.all_archs(platform)

    msg = f'{PRETTY_NAMES[platform]} only supports {sorted(allowed_architectures)} at the moment.'

    if platform != 'linux':
        msg += ' If you want to set emulation architectures on Linux, use CIBW_ARCHS_LINUX instead.'

    if not architectures <= allowed_architectures:
        msg = f'Invalid archs option {architectures}. ' + msg
        raise ValueError(msg)

    if not architectures:
        msg = 'Empty archs option set. ' + msg
        raise ValueError(msg)
