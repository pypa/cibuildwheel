import pytest

import sys
import os
import subprocess

from cibuildwheel import linux, macos, windows


class ArgsInterceptor(object):
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


MOCK_PROJECT_DIR = 'some_project_dir'

@pytest.fixture(autouse=True)
def mock_protection(monkeypatch):
    def fail_on_call(*args, **kwargs):
        raise RuntimeError("This should never be called")

    monkeypatch.setattr(subprocess, 'Popen', fail_on_call)
    monkeypatch.setattr(windows, 'urlopen', fail_on_call)
    monkeypatch.setattr(windows, 'build', fail_on_call)
    monkeypatch.setattr(linux, 'build', fail_on_call)
    monkeypatch.setattr(macos, 'build', fail_on_call)
    monkeypatch.setattr(os.path, 'exists', lambda x: True)
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
