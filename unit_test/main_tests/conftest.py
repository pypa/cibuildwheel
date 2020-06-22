import subprocess
import sys
from pathlib import Path

import pytest

from cibuildwheel import (
    linux,
    macos,
    util,
    windows,
)


class ArgsInterceptor:
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


MOCK_PACKAGE_DIR = Path('some_package_dir')


@pytest.fixture(autouse=True)
def mock_protection(monkeypatch):
    '''
    Ensure that a unit test will never actually run a cibuildwheel 'build'
    function, which shouldn't be run on a developer's machine
    '''

    def fail_on_call(*args, **kwargs):
        raise RuntimeError("This should never be called")

    def ignore_call(*args, **kwargs):
        pass

    monkeypatch.setattr(subprocess, 'Popen', fail_on_call)
    monkeypatch.setattr(util, 'download', fail_on_call)
    monkeypatch.setattr(windows, 'build', fail_on_call)
    monkeypatch.setattr(linux, 'build', fail_on_call)
    monkeypatch.setattr(macos, 'build', fail_on_call)

    monkeypatch.setattr(Path, 'mkdir', ignore_call)


@pytest.fixture(autouse=True)
def fake_package_dir(monkeypatch):
    '''
    Monkey-patch enough for the main() function to run
    '''
    real_path_exists = Path.exists

    def mock_path_exists(path):
        if path == MOCK_PACKAGE_DIR / 'setup.py':
            return True
        else:
            return real_path_exists(path)

    monkeypatch.setattr(Path, 'exists', mock_path_exists)
    monkeypatch.setattr(sys, 'argv', ['cibuildwheel', str(MOCK_PACKAGE_DIR)])


@pytest.fixture(params=['linux', 'macos', 'windows'])
def platform(request, monkeypatch):
    platform_value = request.param
    monkeypatch.setenv('CIBW_PLATFORM', platform_value)
    return platform_value


@pytest.fixture
def intercepted_build_args(platform, monkeypatch):
    intercepted = ArgsInterceptor()
    monkeypatch.setattr(globals()[platform], 'build', intercepted)
    return intercepted
