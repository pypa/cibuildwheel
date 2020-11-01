import os
import time
import sys
from typing import Optional

FOLD_PATTERNS = {
    'azure': ['##[group]{name}', '##[endgroup]'],
    'travis': ['travis_fold:start:{name}', 'travis_fold:end:{name}'],
    'github': ['::group::{name}', '::endgroup::{name}'],
}

PLATFORM_IDENTIFIER_DESCIPTIONS = {
    'manylinux_x86_64': 'Manylinux x86_64',
    'manylinux_i686': 'Manylinux i686',
    'manylinux_aarch64': 'Manylinux aarch64',
    'manylinux_ppc64le': 'Manylinux ppc64le',
    'manylinux_s390x': 'Manylinux s390x',
    'win32': 'Windows 32bit',
    'win_amd64': 'Windows 64bit',
    'macosx_x86_64': 'macOS x86_64',
}


class Logger:
    fold_mode: str
    colors_enabled: bool
    active_build_identifier: Optional[str] = None
    build_start_time: Optional[float] = None
    step_start_time: Optional[float] = None
    active_fold_group_name: Optional[str] = None

    def __init__(self):
        if 'AZURE_HTTP_USER_AGENT' in os.environ:
            self.fold_mode = 'azure'
            self.colors_enabled = True

        elif 'GITHUB_ACTIONS' in os.environ:
            self.fold_mode = 'github'
            self.colors_enabled = True

        elif 'TRAVIS' in os.environ:
            self.fold_mode = 'travis'
            self.colors_enabled = True

        elif 'APPVEYOR' in os.environ:
            self.fold_mode = 'disabled'
            self.colors_enabled = True

        else:
            self.fold_mode = 'disabled'
            self.colors_enabled = False

    def build_start(self, identifier: str):
        c = self.colors
        description = build_description_from_identifier(identifier)
        print()
        print(f'{c.bold}{c.blue}Building {identifier} wheel{c.end}')
        print(f'{description}')
        print()

        self.build_start_time = time.time()
        self.active_build_identifier = identifier

    def build_end(self):
        assert self.build_start_time is not None
        self.step_end()

        print()
        print('---')
        self.build_start_time = None

    def step(self, step_description: str):
        self.step_end()
        self.step_start_time = time.time()
        self.start_fold_group(step_description)

    def step_end(self):
        if self.step_start_time is not None:
            self.end_fold_group()
            c = self.colors
            duration = time.time() - self.step_start_time
            print(f'{c.green}✓ {c.end}{duration:.2f}s'.rjust(78))
            self.step_start_time = None

    def start_fold_group(self, name: str):
        self.end_fold_group()
        self.active_fold_group_name = name
        fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, ('', ''))[0]

        print(fold_start_pattern.format(name=self.active_fold_group_name))
        print()
        # flush to ensure it's output before continuing
        sys.stdout.flush()

    def end_fold_group(self):
        if self.active_fold_group_name:
            fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, ('', ''))[1]
            print(fold_start_pattern.format(name=self.active_fold_group_name))
            sys.stdout.flush()
            self.active_fold_group_name = None

    @property
    def colors(self):
        if self.colors_enabled:
            return colors_enabled
        else:
            return colors_disabled


def build_description_from_identifier(identifier: str):
    python_identifier, _, platform_identifier = identifier.partition('-')

    build_description = ''

    python_interpreter = python_identifier[0:2]
    python_version = python_identifier[2:4]

    if python_interpreter == 'cp':
        build_description += 'CPython'
    elif python_interpreter == 'pp':
        build_description += 'PyPy'
    else:
        raise Exception('unknown python')

    build_description += f' {python_version[0]}.{python_version[1]} '

    try:
        build_description += PLATFORM_IDENTIFIER_DESCIPTIONS[platform_identifier]
    except KeyError as e:
        raise Exception('unknown platform') from e

    return build_description


class Colors():
    red = '\033[31m'
    green = '\033[32m'
    yellow = '\033[33m'
    blue = '\033[34m'
    cyan = '\033[36m'
    bright_green = '\033[92m'
    white = '\033[37m\033[97m'

    bg_grey = '\033[48;5;235m'

    bold = '\033[1m'
    faint = '\033[2m'

    end = '\033[0m'

    class Disabled:
        def __getattr__(self, attr: str):
            return ''


colors_enabled = Colors()
colors_disabled = Colors.Disabled()
