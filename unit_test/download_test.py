from __future__ import annotations

import ssl
import time
import urllib.request

import certifi
import pytest

from cibuildwheel.util.file import download

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Self

DOWNLOAD_URL = "https://cdn.jsdelivr.net/gh/pypa/cibuildwheel@v1.6.3/requirements-dev.txt"
PAYLOAD = b"payload"


def test_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    dest = tmp_path / "file.txt"
    download(DOWNLOAD_URL, dest)
    assert len(dest.read_bytes()) == 134


def test_download_good_ssl_cert_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", certifi.where())
    dest = tmp_path / "file.txt"
    download(DOWNLOAD_URL, dest)
    assert len(dest.read_bytes()) == 134


def test_download_bad_ssl_cert_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad_cafile = tmp_path / "ca.pem"
    bad_cafile.write_text("bad certificates")
    monkeypatch.setenv("SSL_CERT_FILE", str(bad_cafile))
    dest = tmp_path / "file.txt"
    with pytest.raises(ssl.SSLError):
        download(DOWNLOAD_URL, dest)


class FakeResponse:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return PAYLOAD


@pytest.fixture
def fake_network(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[int], tuple[list[str], list[float]]]:
    """Fail the first ``failures`` downloads, recording attempts and sleeps."""

    def setup(failures: int) -> tuple[list[str], list[float]]:
        attempts: list[str] = []
        sleeps: list[float] = []

        def fake_urlopen(url: str, context: object = None) -> FakeResponse:  # noqa: ARG001
            attempts.append(url)
            if len(attempts) <= failures:
                msg = "temporary DNS failure"
                raise OSError(msg)
            return FakeResponse()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(time, "sleep", sleeps.append)
        return attempts, sleeps

    return setup


def test_download_retries_transient_failures(
    fake_network: Callable[[int], tuple[list[str], list[float]]], tmp_path: Path
) -> None:
    attempts, sleeps = fake_network(3)
    dest = tmp_path / "file.txt"

    download(DOWNLOAD_URL, dest)

    assert dest.read_bytes() == PAYLOAD
    assert len(attempts) == 4
    # the wait must grow, so that a long outage is survivable
    assert sleeps == sorted(sleeps)
    assert sleeps[-1] > sleeps[0]


def test_download_backoff_covers_a_minute_outage(
    fake_network: Callable[[int], tuple[list[str], list[float]]], tmp_path: Path
) -> None:
    _, sleeps = fake_network(99)
    dest = tmp_path / "file.txt"

    with pytest.raises(OSError, match="temporary DNS failure"):
        download(DOWNLOAD_URL, dest)

    assert sum(sleeps) >= 60
