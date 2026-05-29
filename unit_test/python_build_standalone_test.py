from __future__ import annotations

import hashlib

from cibuildwheel.util import python_build_standalone

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_download_or_get_from_cache_uses_valid_cached_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cached_file = tmp_path / "python-build-standalone.tar.gz"
    cached_bytes = b"cached archive"
    cached_file.write_bytes(cached_bytes)
    cached_sha256 = hashlib.sha256(cached_bytes).hexdigest()

    was_downloaded = False

    def fake_download(url: str, dest: Path, *, sha256: str | None = None) -> None:
        nonlocal was_downloaded
        was_downloaded = True

    monkeypatch.setattr(python_build_standalone, "download", fake_download)

    archive_path = python_build_standalone._download_or_get_from_cache(
        asset_url="https://example.com/python-build-standalone.tar.gz",
        asset_filename=cached_file.name,
        cache_dir=tmp_path,
        sha256=cached_sha256,
    )

    assert archive_path == cached_file
    assert not was_downloaded


def test_download_or_get_from_cache_redownloads_invalid_cached_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cached_file = tmp_path / "python-build-standalone.tar.gz"
    cached_file.write_bytes(b"bad cache")
    expected_bytes = b"good archive"
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()

    def fake_download(url: str, dest: Path, *, sha256: str | None = None) -> None:
        assert sha256 == expected_sha256
        dest.write_bytes(expected_bytes)

    monkeypatch.setattr(python_build_standalone, "download", fake_download)

    archive_path = python_build_standalone._download_or_get_from_cache(
        asset_url="https://example.com/python-build-standalone.tar.gz",
        asset_filename=cached_file.name,
        cache_dir=tmp_path,
        sha256=expected_sha256,
    )

    assert archive_path == cached_file
    assert cached_file.read_bytes() == expected_bytes
