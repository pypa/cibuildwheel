import ssl

import certifi
import pytest

from cibuildwheel.util.file import download

DOWNLOAD_URL = "https://cdn.jsdelivr.net/gh/pypa/cibuildwheel@v1.6.3/requirements-dev.txt"


def test_download(monkeypatch, tmp_path):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    dest = tmp_path / "file.txt"
    download(DOWNLOAD_URL, dest)
    assert len(dest.read_bytes()) == 134


def test_download_good_ssl_cert_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", certifi.where())
    dest = tmp_path / "file.txt"
    download(DOWNLOAD_URL, dest)
    assert len(dest.read_bytes()) == 134


def test_download_bad_ssl_cert_file(monkeypatch, tmp_path):
    bad_cafile = tmp_path / "ca.pem"
    bad_cafile.write_text("bad certificates")
    monkeypatch.setenv("SSL_CERT_FILE", str(bad_cafile))
    dest = tmp_path / "file.txt"
    with pytest.raises(ssl.SSLError):
        download(DOWNLOAD_URL, dest)
