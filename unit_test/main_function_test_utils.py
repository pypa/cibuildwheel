import sys
import os
import subprocess

import pytest

from cibuildwheel import windows, linux, macos


@pytest.fixture
def argtest():
    class TestArgs(object):
        def __call__(self, **kwargs): 
            self.kwargs = dict(kwargs)
    return TestArgs()

def not_call_mock(*args, **kwargs):
    raise RuntimeError("This should never be called")


def apply_mock_protection(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", not_call_mock)
    monkeypatch.setattr(windows, "urlopen", not_call_mock)
    monkeypatch.setattr(windows, "build", not_call_mock)
    monkeypatch.setattr(linux, "build", not_call_mock)
    monkeypatch.setattr(macos, "build", not_call_mock)
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(sys, "argv", ["python", "abcabc"])