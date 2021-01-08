import functools
import os
import platform as platform_module
import re
import ssl
import sys
import textwrap
import urllib.request
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from time import sleep
from typing import Dict, List, NamedTuple, Optional, Set

import certifi

from .environment import ParsedEnvironment
from .typing import PathOrStr

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


def prepare_command(command: str, **kwargs: PathOrStr) -> str:
    '''
    Preprocesses a command by expanding variables like {python}.

    For example, used in the test_command option to specify the path to the
    project's root.
    '''
    return command.format(python='python', pip='pip', **kwargs)


def get_build_verbosity_extra_flags(level: int) -> List[str]:
    if level > 0:
        return ['-' + level * 'v']
    elif level < 0:
        return ['-' + -level * 'q']
    else:
        return []


class BuildSelector:
    def __init__(self, build_config: str, skip_config: str):
        self.build_patterns = build_config.split()
        self.skip_patterns = skip_config.split()

    def __call__(self, build_id: str) -> bool:
        def match_any(patterns: List[str]) -> bool:
            return any(fnmatch(build_id, pattern) for pattern in patterns)
        return match_any(self.build_patterns) and not match_any(self.skip_patterns)

    def __repr__(self) -> str:
        if not self.skip_patterns:
            return f'BuildSelector({" ".join(self.build_patterns)!r})'
        else:
            return f'BuildSelector({" ".join(self.build_patterns)!r} - {" ".join(self.skip_patterns)!r})'


# Taken from https://stackoverflow.com/a/107717
class Unbuffered:
    def __init__(self, stream):  # type: ignore
        self.stream = stream

    def write(self, data):  # type: ignore
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):  # type: ignore
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):  # type: ignore
        return getattr(self.stream, attr)


def download(url: str, dest: Path) -> None:
    print(f'+ Download {url} to {dest}')
    dest_dir = dest.parent
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    # we've had issues when relying on the host OS' CA certificates on Windows,
    # so we use certifi (this sounds odd but requests also does this by default)
    cafile = os.environ.get('SSL_CERT_FILE', certifi.where())
    context = ssl.create_default_context(cafile=cafile)
    repeat_num = 3
    for i in range(repeat_num):
        try:
            response = urllib.request.urlopen(url, context=context)
        except Exception:
            if i == repeat_num - 1:
                raise
            sleep(3)
            continue
        break

    try:
        dest.write_bytes(response.read())
    finally:
        response.close()


class DependencyConstraints:
    def __init__(self, base_file_path: Path):
        assert base_file_path.exists()
        self.base_file_path = base_file_path.resolve()

    @staticmethod
    def with_defaults() -> 'DependencyConstraints':
        return DependencyConstraints(
            base_file_path=resources_dir / 'constraints.txt'
        )

    def get_for_python_version(self, version: str) -> Path:
        version_parts = version.split('.')

        # try to find a version-specific dependency file e.g. if
        # ./constraints.txt is the base, look for ./constraints-python27.txt
        specific_stem = self.base_file_path.stem + f'-python{version_parts[0]}{version_parts[1]}'
        specific_name = specific_stem + self.base_file_path.suffix
        specific_file_path = self.base_file_path.with_name(specific_name)
        if specific_file_path.exists():
            return specific_file_path
        else:
            return self.base_file_path

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}{self.base_file_path!r})'


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
    def parse_config(config: str, platform: str) -> 'Set[Architecture]':
        result = set()
        for arch_str in re.split(r'[\s,]+', config):
            if arch_str == 'auto':
                result |= Architecture.auto_archs(platform=platform)
            else:
                result.add(Architecture(arch_str))
        return result

    @staticmethod
    def auto_archs(platform: str) -> 'Set[Architecture]':
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


class BuildOptions(NamedTuple):
    package_dir: Path
    output_dir: Path
    build_selector: BuildSelector
    architectures: Set[Architecture]
    environment: ParsedEnvironment
    before_all: str
    before_build: Optional[str]
    repair_command: str
    manylinux_images: Optional[Dict[str, str]]
    dependency_constraints: Optional[DependencyConstraints]
    test_command: Optional[str]
    before_test: Optional[str]
    test_requires: List[str]
    test_extras: str
    build_verbosity: int


resources_dir = Path(__file__).resolve().parent / 'resources'
get_pip_script = resources_dir / 'get-pip.py'
install_certifi_script = resources_dir / "install_certifi.py"


class NonPlatformWheelError(Exception):
    def __init__(self) -> None:
        message = textwrap.dedent('''
            cibuildwheel: Build failed because a pure Python wheel was generated.

            If you intend to build a pure-Python wheel, you don't need cibuildwheel - use
            `pip wheel -w DEST_DIR .` instead.

            If you expected a platform wheel, check your project configuration, or run
            cibuildwheel with CIBW_BUILD_VERBOSITY=1 to view build logs.
        ''')

        super().__init__(message)


def strtobool(val: str) -> bool:
    if val.lower() in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    return False


class CIProvider(Enum):
    travis_ci = 'travis'
    appveyor = 'appveyor'
    circle_ci = 'circle_ci'
    azure_pipelines = 'azure_pipelines'
    github_actions = 'github_actions'
    gitlab = 'gitlab'
    other = 'other'


def detect_ci_provider() -> Optional[CIProvider]:
    if 'TRAVIS' in os.environ:
        return CIProvider.travis_ci
    elif 'APPVEYOR' in os.environ:
        return CIProvider.appveyor
    elif 'CIRCLECI' in os.environ:
        return CIProvider.circle_ci
    elif 'AZURE_HTTP_USER_AGENT' in os.environ:
        return CIProvider.azure_pipelines
    elif 'GITHUB_ACTIONS' in os.environ:
        return CIProvider.github_actions
    elif 'GITLAB_CI' in os.environ:
        return CIProvider.gitlab
    elif strtobool(os.environ.get('CI', 'false')):
        return CIProvider.other
    else:
        return None


PRETTY_NAMES = {'linux': 'Linux', 'macos': 'macOS', 'windows': 'Windows'}

ALLOWED_ARCHITECTURES = {
    'linux': {Architecture.x86_64, Architecture.i686, Architecture.aarch64, Architecture.ppc64le, Architecture.s390x},
    'macos': {Architecture.x86_64, Architecture.universal2, Architecture.arm64},
    'windows': {Architecture.AMD64, Architecture.x86},
}


def allowed_architectures_check(
    name: Literal['linux', 'macos', 'windows'],
    options: BuildOptions,
) -> None:

    allowed_architectures = ALLOWED_ARCHITECTURES[name]

    msg = f'{PRETTY_NAMES[name]} only supports {sorted(allowed_architectures)} at the moment.'

    if name != 'linux':
        msg += ' If you want to set emulation architectures on Linux, use CIBW_ARCHS_LINUX instead.'

    if not options.architectures <= allowed_architectures:
        msg = f'Invalid archs option {options.architectures}. ' + msg
        raise ValueError(msg)

    if not options.architectures:
        msg = 'Empty archs option set. ' + msg
        raise ValueError(msg)


def unwrap(text: str) -> str:
    '''
    Unwraps multi-line text to a single line
    '''
    # remove initial line indent
    text = textwrap.dedent(text)
    # remove leading/trailing whitespace
    text = text.strip()
    # remove consecutive whitespace
    return re.sub(r'\s+', ' ', text)
