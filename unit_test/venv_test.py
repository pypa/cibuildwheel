from __future__ import annotations

import sys

import pytest

from cibuildwheel.venv import _symlink_python_config_scripts

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="config scripts are a POSIX concept"
)


def test_symlink_python_config_scripts(tmp_path: Path) -> None:
    base_bin = tmp_path / "base" / "bin"
    base_bin.mkdir(parents=True)
    base_python = base_bin / "python3"
    base_python.touch()
    # python.org framework builds ship both an unversioned and a versioned script
    (base_bin / "python3-config").touch()
    (base_bin / "python3.12-config").touch()

    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)

    _symlink_python_config_scripts(base_python, venv_bin)

    for name in ("python3-config", "python3.12-config"):
        linked = venv_bin / name
        assert linked.is_symlink()
        assert linked.resolve() == (base_bin / name).resolve()


def test_symlink_python_config_scripts_no_config(tmp_path: Path) -> None:
    """Interpreters without a config script (PyPy, GraalPy, ...) must not fail."""
    base_bin = tmp_path / "base" / "bin"
    base_bin.mkdir(parents=True)
    base_python = base_bin / "pypy3"
    base_python.touch()
    # PyPy ships pypy3-config, which must not be picked up as python*-config
    (base_bin / "pypy3-config").touch()

    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)

    _symlink_python_config_scripts(base_python, venv_bin)

    assert list(venv_bin.iterdir()) == []


def test_symlink_python_config_scripts_existing_not_overwritten(tmp_path: Path) -> None:
    base_bin = tmp_path / "base" / "bin"
    base_bin.mkdir(parents=True)
    base_python = base_bin / "python3"
    base_python.touch()
    (base_bin / "python3-config").touch()

    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    # a pre-existing real file should be left untouched
    existing = venv_bin / "python3-config"
    existing.write_text("#!/bin/sh\n")

    _symlink_python_config_scripts(base_python, venv_bin)

    assert not existing.is_symlink()
    assert existing.read_text() == "#!/bin/sh\n"
