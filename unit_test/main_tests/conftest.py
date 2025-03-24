import contextlib
import platform as platform_module
import subprocess
import sys
from pathlib import Path

import pytest

from cibuildwheel import __main__, architecture
from cibuildwheel.platforms import linux, macos, pyodide, windows
from cibuildwheel.util import file


class ArgsInterceptor:
    def __init__(self) -> None:
        self.call_count = 0
        self.args: tuple[object, ...] | None = None
        self.kwargs: dict[str, object] | None = None

    def __call__(self, *args: object, **kwargs: object) -> None:
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
    monkeypatch.setattr(file, "download", fail_on_call)
    monkeypatch.setattr(windows, "build", fail_on_call)
    monkeypatch.setattr(linux, "build", fail_on_call)
    monkeypatch.setattr(macos, "build", fail_on_call)
    monkeypatch.setattr(pyodide, "build", fail_on_call)
    monkeypatch.setattr(Path, "mkdir", ignore_call)
    monkeypatch.setattr(architecture, "_check_aarch32_el0", lambda: True)


@pytest.fixture(autouse=True)
def fake_package_dir_autouse(fake_package_dir):
    pass


@pytest.fixture(autouse=True)
def disable_print_wheels(monkeypatch):
    @contextlib.contextmanager
    def empty_cm(*args, **kwargs):
        yield

    monkeypatch.setattr(__main__, "print_new_wheels", empty_cm)


@pytest.fixture
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


@pytest.fixture
def intercepted_build_args(monkeypatch):
    intercepted = ArgsInterceptor()

    monkeypatch.setattr(linux, "build", intercepted)
    monkeypatch.setattr(macos, "build", intercepted)
    monkeypatch.setattr(windows, "build", intercepted)
    monkeypatch.setattr(pyodide, "build", intercepted)

    yield intercepted

    # check that intercepted_build_args only ever had one set of args
    assert intercepted.call_count <= 1
