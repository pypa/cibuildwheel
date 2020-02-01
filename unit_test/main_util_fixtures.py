import pytest

import sys
import os
import subprocess

from cibuildwheel import linux, macos, windows, util


class ArgsInterceptor(object):
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


MOCK_PROJECT_DIR = 'some_project_dir'

@pytest.fixture(autouse=True)
def mock_protection(monkeypatch):
    '''
    Ensure that a unit test will never actually run a cibuildwheel 'build'
    function, which shouldn't be run on a developer's machine
    '''

    def fail_on_call(*args, **kwargs):
        raise RuntimeError("This should never be called")

    monkeypatch.setattr(subprocess, 'Popen', fail_on_call)
    monkeypatch.setattr(util, 'download', fail_on_call)
    monkeypatch.setattr(windows, 'build', fail_on_call)
    monkeypatch.setattr(linux, 'build', fail_on_call)
    monkeypatch.setattr(macos, 'build', fail_on_call)

@pytest.fixture(autouse=True)
def fake_project_dir(monkeypatch):
    '''
    Monkey-patch enough for the main() function to run
    '''

    real_os_path_exists = os.path.exists
    def mock_os_path_exists(path):
        if path == os.path.join(MOCK_PROJECT_DIR, 'setup.py'):
            return True
        else:
            return real_os_path_exists(path)

    monkeypatch.setattr(os.path, 'exists', mock_os_path_exists)
    monkeypatch.setattr(sys, 'argv', ['cibuildwheel', MOCK_PROJECT_DIR])


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
