import os
import urllib.request
from fnmatch import fnmatch
from time import sleep

from typing import Dict, List, NamedTuple, Optional, Type, TypeVar

from .environment import ParsedEnvironment


def prepare_command(command: str, **kwargs: str) -> str:
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
        return 'BuildSelector({!r} - {!r})'.format(' '.join(self.build_patterns), ' '.join(self.skip_patterns))


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


def download(url: str, dest: str) -> None:
    print('+ Download ' + url + ' to ' + dest)
    dest_dir = os.path.dirname(dest)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    repeat_num = 3
    for i in range(repeat_num):
        try:
            response = urllib.request.urlopen(url)
        except Exception:
            if i == repeat_num - 1:
                raise
            sleep(3)
            continue
        break

    try:
        with open(dest, 'wb') as file:
            file.write(response.read())
    finally:
        response.close()


DependencyConstraints_T = TypeVar('DependencyConstraints_T', bound='DependencyConstraints')


class DependencyConstraints:
    def __init__(self, base_file_path: str):
        assert os.path.exists(base_file_path)
        self.base_file_path = os.path.abspath(base_file_path)

    @classmethod
    def with_defaults(cls: Type[DependencyConstraints_T]) -> DependencyConstraints_T:
        return cls(
            base_file_path=os.path.join(os.path.dirname(__file__), 'resources', 'constraints.txt')
        )

    def get_for_python_version(self, version: str) -> str:
        version_parts = version.split('.')

        # try to find a version-specific dependency file e.g. if
        # ./constraints.txt is the base, look for ./constraints-python27.txt
        base, ext = os.path.splitext(self.base_file_path)
        specific = base + '-python{}{}'.format(version_parts[0], version_parts[1])
        specific_file_path = specific + ext
        if os.path.exists(specific_file_path):
            return specific_file_path
        else:
            return self.base_file_path


class BuildOptions(NamedTuple):
    package_dir: str
    output_dir: str
    test_command: Optional[str]
    test_requires: List[str]
    test_extras: str
    before_build: Optional[str]
    build_verbosity: int
    build_selector: BuildSelector
    repair_command: str
    environment: ParsedEnvironment
    before_test: str
    dependency_constraints: Optional[DependencyConstraints]
    manylinux_images: Optional[Dict[str, str]]


resources_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources'))
get_pip_script = os.path.join(resources_dir, 'get-pip.py')
