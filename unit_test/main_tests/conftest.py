import contextlib
import platform as platform_module
import subprocess
import sys
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

import pytest

from cibuildwheel import architecture
from cibuildwheel.logger import Logger
from cibuildwheel.platforms import android, ios, linux, macos, pyodide, windows
from cibuildwheel.util import file


class ArgsInterceptor:
    def __init__(self) -> None:
        self.call_count = 0
        self.args: tuple[Any, ...] = ()
        self.kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.call_count += 1
        self.args = args
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def mock_protection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that a unit test will never actually run a cibuildwheel 'build'
    function, which shouldn't be run on a developer's machine
    """

    def fail_on_call(*args: object, **kwargs: object) -> None:
        msg = "This should never be called"
        raise RuntimeError(msg)

    def ignore_call(*args: object, **kwargs: object) -> None:
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
def fake_package_dir_autouse(fake_package_dir: list[str]) -> None:
    pass


@pytest.fixture(autouse=True)
def disable_print_wheels(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.contextmanager
    def empty_cm(*args: object, **kwargs: object) -> Generator[None, None, None]:
        yield

    monkeypatch.setattr(Logger, "print_summary", empty_cm)


@pytest.fixture
def allow_empty(monkeypatch: pytest.MonkeyPatch, fake_package_dir: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", [*fake_package_dir, "--allow-empty"])


@pytest.fixture(params=["linux", "macos", "windows"])
def platform(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str:
    platform_value: str = request.param
    monkeypatch.setenv("CIBW_PLATFORM", platform_value)

    if platform_value == "windows":
        monkeypatch.setattr(platform_module, "machine", lambda: "AMD64")
    else:
        monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    if platform_value == "macos":
        monkeypatch.setattr(macos, "get_macos_version", lambda: (11, 1))

    return platform_value


@pytest.fixture
def intercepted_build_args(monkeypatch: pytest.MonkeyPatch) -> Iterator[ArgsInterceptor]:
    intercepted = ArgsInterceptor()

    monkeypatch.setattr(android, "build", intercepted)
    monkeypatch.setattr(ios, "build", intercepted)
    monkeypatch.setattr(linux, "build", intercepted)
    monkeypatch.setattr(macos, "build", intercepted)
    monkeypatch.setattr(pyodide, "build", intercepted)
    monkeypatch.setattr(windows, "build", intercepted)

    yield intercepted

    # check that intercepted_build_args only ever had one set of args
    assert intercepted.call_count <= 1
