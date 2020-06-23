import os
import urllib.request
from fnmatch import fnmatch
from pathlib import Path
from time import sleep

from typing import Dict, List, NamedTuple, Optional, Union

from .environment import ParsedEnvironment


def prepare_command(command: str, **kwargs: Union[str, os.PathLike]) -> str:
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


class BuildOptions(NamedTuple):
    package_dir: Path
    output_dir: Path
    build_selector: BuildSelector
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
