import contextlib
import fnmatch
import itertools
import os
import re
import ssl
import textwrap
import time
import urllib.request
from enum import Enum
from pathlib import Path
from time import sleep
from typing import Dict, Iterator, List, NamedTuple, Optional, Set

import bracex
import certifi
import toml
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .architecture import Architecture
from .environment import ParsedEnvironment
from .typing import PathOrStr, PlatformName

resources_dir = Path(__file__).parent / 'resources'

get_pip_script = resources_dir / 'get-pip.py'
install_certifi_script = resources_dir / "install_certifi.py"


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


def read_python_configs(config: PlatformName) -> List[Dict[str, str]]:
    input_file = resources_dir / 'build-platforms.toml'
    loaded_file = toml.load(input_file)
    results: List[Dict[str, str]] = list(loaded_file[config]['python_configurations'])
    return results


class IdentifierSelector:
    """
    This class holds a set of build/skip patterns. You call an instance with a
    build identifier, and it returns True if that identifier should be
    included. Only call this on valid identifiers, ones that have at least 2
    numeric digits before the first dash.
    """

    def __init__(self, *, build_config: str, skip_config: str, requires_python: Optional[SpecifierSet] = None):
        self.build_patterns = build_config.split()
        self.skip_patterns = skip_config.split()
        self.requires_python = requires_python

    def __call__(self, build_id: str) -> bool:
        # Filter build selectors by python_requires if set
        if self.requires_python is not None:
            py_ver_str = build_id.split('-')[0]
            major = int(py_ver_str[2])
            minor = int(py_ver_str[3:])
            version = Version(f"{major}.{minor}.99")
            if not self.requires_python.contains(version):
                return False

        build_patterns = itertools.chain.from_iterable(bracex.expand(p) for p in self.build_patterns)
        skip_patterns = itertools.chain.from_iterable(bracex.expand(p) for p in self.skip_patterns)

        build: bool = any(fnmatch.fnmatch(build_id, pat) for pat in build_patterns)
        skip: bool = any(fnmatch.fnmatch(build_id, pat) for pat in skip_patterns)
        return build and not skip

    def __repr__(self) -> str:
        if not self.skip_patterns:
            return f'{self.__class__.__name__}({" ".join(self.build_patterns)!r})'
        else:
            return f'{self.__class__.__name__}({" ".join(self.build_patterns)!r} - {" ".join(self.skip_patterns)!r})'


class BuildSelector(IdentifierSelector):
    pass


# Note that requires-python is not needed for TestSelector, as you can't test
# what you can't build.
class TestSelector(IdentifierSelector):
    def __init__(self, *, skip_config: str):
        super().__init__(build_config="*", skip_config=skip_config)


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
    test_selector: TestSelector
    before_test: Optional[str]
    test_requires: List[str]
    test_extras: str
    build_verbosity: int


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
    return val.lower() in {'y', 'yes', 't', 'true', 'on', '1'}


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


@contextlib.contextmanager
def print_new_wheels(msg: str, output_dir: Path) -> Iterator[None]:
    '''
    Prints the new items in a directory upon exiting. The message to display
    can include {n} for number of wheels, {s} for total number of seconds,
    and/or {m} for total number of minutes. Does not print anything if this
    exits via exception.
    '''

    start_time = time.time()
    existing_contents = set(output_dir.iterdir())
    yield
    final_contents = set(output_dir.iterdir())
    new_contents = final_contents - existing_contents
    n = len(new_contents)
    s = time.time() - start_time
    m = s / 60
    print(msg.format(n=n, s=s, m=m), *sorted(f"  {f.name}" for f in new_contents), sep="\n")
