import os
import sys
from pathlib import Path

import pytest

import cibuildwheel.venv
from cibuildwheel.venv import activate_virtualenv, find_uv, virtualenv


def test_activate_virtualenv(tmp_path: Path) -> None:
    venv_path = tmp_path / "venv"
    env = activate_virtualenv(venv_path, env={"PATH": "/usr/bin"})
    paths = env["PATH"].split(os.pathsep)
    if sys.platform == "win32":
        assert paths[:2] == [str(venv_path), str(venv_path / "Scripts")]
    else:
        assert paths[0] == str(venv_path / "bin")
    assert paths[-1] == "/usr/bin"
    assert env["VIRTUAL_ENV"] == str(venv_path)


def test_activate_virtualenv_base_python_bin_dir(tmp_path: Path) -> None:
    venv_path = tmp_path / "venv"
    base_bin = tmp_path / "base" / "bin"
    env = activate_virtualenv(venv_path, env={"PATH": "/usr/bin"}, base_python_bin_dir=base_bin)
    paths = env["PATH"].split(os.pathsep)
    # the base interpreter's bin dir comes right after the venv, so scripts
    # like python3-config resolve to the matching interpreter (see #2021)
    if sys.platform == "win32":
        assert paths[:3] == [str(venv_path), str(venv_path / "Scripts"), str(base_bin)]
    else:
        assert paths[:2] == [str(venv_path / "bin"), str(base_bin)]
    assert paths[-1] == "/usr/bin"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only behavior")
@pytest.mark.skipif(find_uv() is None, reason="requires uv")
def test_virtualenv_puts_base_python_bin_dir_on_path(tmp_path: Path) -> None:
    version = "{}.{}".format(*sys.version_info[:2])
    venv_path = tmp_path / "venv"
    env = virtualenv(
        version, Path(sys.executable), venv_path, None, use_uv=True, env={"PATH": "/usr/bin"}
    )
    paths = env["PATH"].split(os.pathsep)
    assert paths == [str(venv_path / "bin"), str(Path(sys.executable).parent), "/usr/bin"]


@pytest.mark.skipif(find_uv() is None, reason="requires uv")
def test_virtualenv_no_base_python_bin_dir_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cibuildwheel.venv, "_IS_WIN", True)
    version = "{}.{}".format(*sys.version_info[:2])
    venv_path = tmp_path / "venv"
    env = virtualenv(
        version, Path(sys.executable), venv_path, None, use_uv=True, env={"PATH": "/usr/bin"}
    )
    paths = env["PATH"].split(os.pathsep)
    assert str(Path(sys.executable).parent) not in paths
