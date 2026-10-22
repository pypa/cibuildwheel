import os
import subprocess
import sys
from pathlib import Path

import certifi
import pytest
from packaging.version import Version

import cibuildwheel.venv
from cibuildwheel.venv import (
    activate_virtualenv,
    find_uv,
    target_marker_env,
    uv_ca_warning,
    virtualenv,
)


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


@pytest.mark.skipif(find_uv() is None, reason="requires uv")
@pytest.mark.parametrize(("version", "expected"), [("3.9", True), ("3.10", False)])
def test_virtualenv_pip_cert(tmp_path: Path, version: str, *, expected: bool) -> None:
    env = virtualenv(
        version, Path(sys.executable), tmp_path / "venv", None, use_uv=True, env={"PATH": ""}
    )
    assert ("PIP_CERT" in env) == expected
    if expected:
        assert env["PIP_CERT"] == certifi.where()


@pytest.mark.skipif(find_uv() is None, reason="requires uv")
def test_virtualenv_pip_cert_graalpy(tmp_path: Path) -> None:
    # truststore is not supported on GraalPy, so pip uses its bundled certifi
    env = virtualenv(
        "3.12",
        Path(sys.executable),
        tmp_path / "venv",
        None,
        use_uv=True,
        env={"PATH": ""},
        marker_env=target_marker_env(implementation_id="gp312_250"),
    )
    assert env["PIP_CERT"] == certifi.where()


@pytest.mark.skipif(find_uv() is None, reason="requires uv")
def test_virtualenv_pip_cert_user_override(tmp_path: Path) -> None:
    env = virtualenv(
        "3.9",
        Path(sys.executable),
        tmp_path / "venv",
        None,
        use_uv=True,
        env={"PATH": "", "PIP_CERT": "/my/cert.pem"},
    )
    assert env["PIP_CERT"] == "/my/cert.pem"


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("uv 0.13.3 (abc 2026-10-01)", True),
        ("uv 0.9.0", True),
        ("uv 0.13.4 (Homebrew 2026-10-20 aarch64-apple-darwin)", False),
        ("uv 1.0.0", False),
        ("garbage", False),
    ],
)
def test_uv_ca_warning(monkeypatch: pytest.MonkeyPatch, output: str, *, expected: bool) -> None:
    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout=output + "\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    warning = uv_ca_warning(Path("uv"))
    if expected:
        assert warning is not None
        assert output.split()[1] in warning
    else:
        assert warning is None


def test_virtualenv_host_call_ignores_target_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # virtualenv runs on the host Python, so target settings like PYTHON_GIL=0 must not leak in
    calls: list[dict[str, str] | None] = []
    monkeypatch.setattr(
        cibuildwheel.venv, "_ensure_virtualenv", lambda _: (tmp_path / "v.pyz", Version("21.0"))
    )
    monkeypatch.setattr(cibuildwheel.venv, "call", lambda *_, env=None: calls.append(env))

    venv_env = virtualenv(
        "3.9",
        Path(sys.executable),
        tmp_path / "venv",
        None,
        use_uv=False,
        env={"PATH": "", "PYTHON_GIL": "0"},
        pip_version="26.0.1",
    )

    assert venv_env["PYTHON_GIL"] == "0"
    assert venv_env["PIP_CERT"] == certifi.where()
    assert calls == [None]
