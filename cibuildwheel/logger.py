from contextlib import contextmanager
import os
import time
import typing

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

    @contextmanager
    def build(self, identifier: str):
        c = self.colors
        print(f'{c.bold}Building {build_description_from_identifier(identifier)} wheel{c.end}')
        print(f'Identifier: {identifier}')

        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time
            print(f'{c.green}Build {c.bg_grey}{identifier}{c.end}{c.green} completed in {duration:.2f}s{c.end}')
        except Exception:
            duration = time.time() - start_time
            print(f'{c.red}Build {c.bg_grey}{identifier}{c.end}{c.red} failed in {duration:.2f}s{c.end}')
            raise

    @contextmanager
    def step(self, name: str):
        c = self.colors
        start_time = time.time()

        try:
            with self.fold_group(name):
                yield
            duration = time.time() - start_time
            print(f'{c.green}✓ {c.faint}[{duration:.2f}]{c.end}')
        except Exception:
            raise

    @contextmanager
    def fold_group(self, name: str):
        fold_start_pattern, fold_end_pattern = FOLD_PATTERNS.get(self.fold_mode, ('', ''))
        print(fold_start_pattern.format(name=name))
        try:
            yield
        finally:
            print(fold_end_pattern.format(name=name))

    @property
    def colors(self):
        if self.colors_enabled:
            return colors_enabled
        else:
            return colors_disabled


def build_description_from_identifier(identifier):
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

    bg_grey = '\033[48;5;244m'

    bold = '\033[1m'
    faint = '\033[2m'

    end = '\033[0m'

    class Disabled:
        def __getattr__(self, attr):
            return ''


colors_enabled = Colors()
colors_disabled = Colors.Disabled()
