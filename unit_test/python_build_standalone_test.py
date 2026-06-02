from __future__ import annotations

import subprocess

import pytest

from cibuildwheel.util import python_build_standalone as pbs

# Real-world `ldd --version` outputs.
GLIBC_STDOUT = "ldd (Ubuntu GLIBC 2.35-0ubuntu3.1) 2.35\n"
MUSL_STDERR = "musl libc (x86_64)\nVersion 1.2.4\nDynamic Program Loader\n"


def _fake_ldd(stdout: str = "", stderr: str = ""):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr=stderr)

    return run


def test_is_musl_libc_detects_musl(monkeypatch):
    # musl's ldd prints to stderr and exits non-zero, but capture both streams
    monkeypatch.setattr(subprocess, "run", _fake_ldd(stderr=MUSL_STDERR))
    assert pbs._is_musl_libc() is True


def test_is_musl_libc_detects_glibc(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_ldd(stdout=GLIBC_STDOUT))
    assert pbs._is_musl_libc() is False


def test_is_musl_libc_missing_ldd(monkeypatch):
    def run(*args, **kwargs):
        raise FileNotFoundError("ldd")

    monkeypatch.setattr(subprocess, "run", run)
    assert pbs._is_musl_libc() is False


@pytest.mark.parametrize(
    ("musl", "expected_libc"),
    [(True, "musl"), (False, "gnu")],
)
def test_linux_platform_identifiers_libc(monkeypatch, musl, expected_libc):
    monkeypatch.setattr(pbs.platform, "system", lambda: "Linux")
    monkeypatch.setattr(pbs.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(pbs, "_is_musl_libc", lambda: musl)

    arch, platform_id, libc = pbs._get_platform_identifiers()
    assert arch == "x86_64"
    assert platform_id == "unknown-linux"
    assert libc == expected_libc
