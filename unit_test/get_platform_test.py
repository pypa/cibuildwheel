import contextlib
import sys
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import setuptools._distutils.util

from cibuildwheel.ci import CIProvider, detect_ci_provider
from cibuildwheel.errors import FatalError
from cibuildwheel.platforms.windows import PythonConfiguration, setup_setuptools_cross_compile

# monkeypatching os.name is too flaky. E.g. It works on my machine, but fails in pipeline
if not sys.platform.startswith("win") and not TYPE_CHECKING:
    pytest.skip("Windows-only tests", allow_module_level=True)


@contextlib.contextmanager
def patched_environment(
    monkeypatch: pytest.MonkeyPatch, environment: dict[str, str]
) -> Generator[None, None, None]:
    with monkeypatch.context() as mp:
        for envvar, val in environment.items():
            mp.setenv(name=envvar, value=val)
        yield


def test_x86(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arch = "32"
    environment: dict[str, str] = {}

    configuration = PythonConfiguration(
        version="irrelevant", arch=arch, identifier="irrelevant", url=None
    )

    setup_setuptools_cross_compile(tmp_path, configuration, tmp_path, environment)
    with patched_environment(monkeypatch, environment):
        target_platform = setuptools._distutils.util.get_platform()

    assert environment["VSCMD_ARG_TGT_ARCH"] == "x86"
    assert target_platform == "win32"


def test_x64(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arch = "64"
    environment: dict[str, str] = {}

    configuration = PythonConfiguration(
        version="irrelevant", arch=arch, identifier="irrelevant", url=None
    )

    setup_setuptools_cross_compile(tmp_path, configuration, tmp_path, environment)
    with patched_environment(monkeypatch, environment):
        target_platform = setuptools._distutils.util.get_platform()

    assert environment["VSCMD_ARG_TGT_ARCH"] == "x64"
    assert target_platform == "win-amd64"


@pytest.mark.skipif(
    detect_ci_provider() == CIProvider.azure_pipelines, reason="arm64 not recognised on azure"
)
def test_arm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arch = "ARM64"
    environment: dict[str, str] = {}

    configuration = PythonConfiguration(
        version="irrelevant", arch=arch, identifier="irrelevant", url=None
    )

    setup_setuptools_cross_compile(tmp_path, configuration, tmp_path, environment)
    with patched_environment(monkeypatch, environment):
        target_platform = setuptools._distutils.util.get_platform()

    assert environment["VSCMD_ARG_TGT_ARCH"] == "arm64"
    assert target_platform == "win-arm64"


def test_env_set(tmp_path: Path) -> None:
    arch = "32"
    environment = {"VSCMD_ARG_TGT_ARCH": "x64"}

    configuration = PythonConfiguration(
        version="irrelevant", arch=arch, identifier="irrelevant", url=None
    )

    with pytest.raises(FatalError, match="VSCMD_ARG_TGT_ARCH"):
        setup_setuptools_cross_compile(tmp_path, configuration, tmp_path, environment)


def test_env_blank(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arch = "32"
    environment = {"VSCMD_ARG_TGT_ARCH": ""}

    configuration = PythonConfiguration(
        version="irrelevant", arch=arch, identifier="irrelevant", url=None
    )

    setup_setuptools_cross_compile(tmp_path, configuration, tmp_path, environment)
    with patched_environment(monkeypatch, environment):
        target_platform = setuptools._distutils.util.get_platform()

    assert environment["VSCMD_ARG_TGT_ARCH"] == "x86"
    assert target_platform == "win32"
