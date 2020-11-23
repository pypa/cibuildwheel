import codecs
import os
import re
import sys
import time
from typing import Optional, Union

from cibuildwheel.util import CIProvider, detect_ci_provider

DEFAULT_FOLD_PATTERN = ('{name}', '')
FOLD_PATTERNS = {
    'azure': ('##[group]{name}', '##[endgroup]'),
    'travis': ('travis_fold:start:{identifier}\n{name}', 'travis_fold:end:{identifier}'),
    'github': ('::group::{name}', '::endgroup::{name}'),
}

PLATFORM_IDENTIFIER_DESCIPTIONS = {
    'manylinux_x86_64': 'manylinux x86_64',
    'manylinux_i686': 'manylinux i686',
    'manylinux_aarch64': 'manylinux aarch64',
    'manylinux_ppc64le': 'manylinux ppc64le',
    'manylinux_s390x': 'manylinux s390x',
    'win32': 'Windows 32bit',
    'win_amd64': 'Windows 64bit',
    'macosx_x86_64': 'macOS x86_64',
}


class Logger:
    fold_mode: str
    colors_enabled: bool
    unicode_enabled: bool
    active_build_identifier: Optional[str] = None
    build_start_time: Optional[float] = None
    step_start_time: Optional[float] = None
    active_fold_group_name: Optional[str] = None

    def __init__(self):
        if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
            # the encoding on Windows can be a 1-byte charmap, but all CIs
            # support utf8, so we hardcode that
            sys.stdout.reconfigure(encoding='utf8')

        self.unicode_enabled = file_supports_unicode(sys.stdout)

        ci_provider = detect_ci_provider()

        if ci_provider == CIProvider.azure_pipelines:
            self.fold_mode = 'azure'
            self.colors_enabled = True

        elif ci_provider == CIProvider.github_actions:
            self.fold_mode = 'github'
            self.colors_enabled = True

        elif ci_provider == CIProvider.travis_ci:
            self.fold_mode = 'travis'
            self.colors_enabled = True

        elif ci_provider == CIProvider.appveyor:
            self.fold_mode = 'disabled'
            self.colors_enabled = True

        else:
            self.fold_mode = 'disabled'
            self.colors_enabled = file_supports_color(sys.stdout)

    def build_start(self, identifier: str):
        self.step_end()
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
        assert self.active_build_identifier is not None
        self.step_end()

        c = self.colors
        s = self.symbols
        duration = time.time() - self.build_start_time

        print()
        print(f'{c.green}{s.done} {c.end}{self.active_build_identifier} finished in {duration:.2f}s')
        self.build_start_time = None
        self.active_build_identifier = None

    def step(self, step_description: str):
        self.step_end()
        self.step_start_time = time.time()
        self._start_fold_group(step_description)

    def step_end(self, success=True):
        if self.step_start_time is not None:
            self._end_fold_group()
            c = self.colors
            s = self.symbols
            duration = time.time() - self.step_start_time
            if success:
                print(f'{c.green}{s.done} {c.end}{duration:.2f}s'.rjust(78))
            else:
                print(f'{c.red}{s.error} {c.end}{duration:.2f}s'.rjust(78))

            self.step_start_time = None

    def error(self, error: Union[Exception, str]):
        self.step_end(success=False)
        print()

        if self.fold_mode == 'github':
            print(f'::error::{error}')
        else:
            c = self.colors
            print(f'{c.bright_red}Error{c.end} {error}')

    def _start_fold_group(self, name: str):
        self._end_fold_group()
        self.active_fold_group_name = name
        fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, DEFAULT_FOLD_PATTERN)[0]
        identifier = self._fold_group_identifier(name)

        print(fold_start_pattern.format(name=self.active_fold_group_name, identifier=identifier))
        print()
        sys.stdout.flush()

    def _end_fold_group(self):
        if self.active_fold_group_name:
            fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, DEFAULT_FOLD_PATTERN)[1]
            identifier = self._fold_group_identifier(self.active_fold_group_name)
            print(fold_start_pattern.format(name=self.active_fold_group_name, identifier=identifier))
            sys.stdout.flush()
            self.active_fold_group_name = None

    def _fold_group_identifier(self, name: str):
        '''
        Travis doesn't like fold groups identifiers that have spaces in. This
        method converts them to ascii identifiers
        '''
        # whitespace to underscores
        identifier = re.sub(r'\s+', '_', name)
        # remove non-alphanum
        identifier = re.sub(r'[^A-Za-z\d_]+', '', identifier)
        # trim underscores
        identifier = identifier.strip('_')
        # lowercase, shorten
        return identifier.lower()[:20]

    @property
    def colors(self):
        if self.colors_enabled:
            return Colors.enabled
        else:
            return Colors.disabled

    @property
    def symbols(self):
        if self.unicode_enabled:
            return Symbols.unicode
        else:
            return Symbols.ascii


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


class Colors:
    class Enabled:
        red = '\033[31m'
        green = '\033[32m'
        yellow = '\033[33m'
        blue = '\033[34m'
        cyan = '\033[36m'
        bright_red = '\033[91m'
        bright_green = '\033[92m'
        white = '\033[37m\033[97m'

        bg_grey = '\033[48;5;235m'

        bold = '\033[1m'
        faint = '\033[2m'

        end = '\033[0m'

    class Disabled:
        def __getattr__(self, attr: str) -> str:
            return ''

    enabled = Enabled()
    disabled = Disabled()


class Symbols:
    class Unicode:
        done = '✓'
        error = '✕'

    class Ascii:
        done = 'done'
        error = 'failed'

    unicode = Unicode()
    ascii = Ascii()


def file_supports_color(file_obj):
    """
    Returns True if the running system's terminal supports color.
    """
    plat = sys.platform
    supported_platform = (plat != 'win32' or 'ANSICON' in os.environ)

    is_a_tty = file_is_a_tty(file_obj)

    return (supported_platform and is_a_tty)


def file_is_a_tty(file_obj):
    return hasattr(file_obj, 'isatty') and file_obj.isatty()


def file_supports_unicode(file_obj):
    encoding = getattr(file_obj, 'encoding', None)
    if not encoding:
        return False

    codec_info = codecs.lookup(encoding)

    return ('utf' in codec_info.name)


'''
Global instance of the Logger.
'''
# (there's only one stdout per-process, so a global instance is justified)
log = Logger()
