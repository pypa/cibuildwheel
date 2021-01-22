import functools
import platform as platform_module
import re
from enum import Enum
from typing import Set

from .typing import PlatformName, assert_never

PRETTY_NAMES = {'linux': 'Linux', 'macos': 'macOS', 'windows': 'Windows'}


@functools.total_ordering
class Architecture(Enum):
    value: str

    # mac/linux archs
    x86_64 = 'x86_64'
    i686 = 'i686'
    aarch64 = 'aarch64'
    ppc64le = 'ppc64le'
    s390x = 's390x'

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
        return result

    @staticmethod
    def all_archs(platform: PlatformName) -> 'Set[Architecture]':
        if platform == 'linux':
            return {Architecture.x86_64, Architecture.i686, Architecture.aarch64, Architecture.ppc64le, Architecture.s390x}
        elif platform == 'macos':
            return {Architecture.x86_64}
        elif platform == 'windows':
            return {Architecture.x86, Architecture.AMD64}
        else:
            assert_never(platform)


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
