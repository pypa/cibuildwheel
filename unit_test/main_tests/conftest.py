from __future__ import annotations

import contextlib
import platform as platform_module
import subprocess
import sys
from pathlib import Path

import pytest

from cibuildwheel import linux, macos, util, windows


class ArgsInterceptor:
    def __init__(self):
        self.call_count = 0
        self.args = None
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.args = args
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def mock_protection(monkeypatch):
    """
    Ensure that a unit test will never actually run a cibuildwheel 'build'
    function, which shouldn't be run on a developer's machine
    """

    def fail_on_call(*args, **kwargs):
        msg = "This should never be called"
        raise RuntimeError(msg)

    def ignore_call(*args, **kwargs):
        pass

    monkeypatch.setattr(subprocess, "Popen", fail_on_call)
    monkeypatch.setattr(util, "download", fail_on_call)
    monkeypatch.setattr(windows, "build", fail_on_call)
    monkeypatch.setattr(linux, "build", fail_on_call)
    monkeypatch.setattr(macos, "build", fail_on_call)

    monkeypatch.setattr(Path, "mkdir", ignore_call)


@pytest.fixture(autouse=True)
def fake_package_dir_autouse(fake_package_dir):  # noqa: ARG001
    pass


@pytest.fixture(autouse=True)
def disable_print_wheels(monkeypatch):
    @contextlib.contextmanager
    def empty_cm(*args, **kwargs):
        yield

    monkeypatch.setattr(util, "print_new_wheels", empty_cm)


@pytest.fixture()
def allow_empty(monkeypatch, fake_package_dir):
    monkeypatch.setattr(sys, "argv", [*fake_package_dir, "--allow-empty"])


@pytest.fixture(params=["linux", "macos", "windows"])
def platform(request, monkeypatch):
    platform_value = request.param
    monkeypatch.setenv("CIBW_PLATFORM", platform_value)

    if platform_value == "windows":
        monkeypatch.setattr(platform_module, "machine", lambda: "AMD64")
    else:
        monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    if platform_value == "macos":
        monkeypatch.setattr(macos, "get_macos_version", lambda: (11, 1))

    return platform_value


@pytest.fixture()
def intercepted_build_args(monkeypatch):
    intercepted = ArgsInterceptor()

    monkeypatch.setattr(linux, "build", intercepted)
    monkeypatch.setattr(macos, "build", intercepted)
    monkeypatch.setattr(windows, "build", intercepted)

    yield intercepted

    # check that intercepted_build_args only ever had one set of args
    assert intercepted.call_count <= 1
