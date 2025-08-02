import errno
import shutil
import sys

import pytest

import cibuildwheel.__main__ as main_module
from cibuildwheel.__main__ import main


def test_clean_cache_when_cache_exists(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "cibw_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    fake_cache_dir.mkdir(parents=True, exist_ok=True)
    assert fake_cache_dir.exists()

    dummy_file = fake_cache_dir / "dummy.txt"
    dummy_file.write_text("hello")

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    assert f"Clearing cache directory: {fake_cache_dir}" in out
    assert "Cache cleared successfully." in out
    assert not fake_cache_dir.exists()


def test_clean_cache_when_cache_does_not_exist(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "nonexistent_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, err = capfd.readouterr()
    assert f"Cache directory does not exist: {fake_cache_dir}" in out


def test_clean_cache_with_error(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "cibw_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    fake_cache_dir.mkdir(parents=True, exist_ok=True)
    assert fake_cache_dir.exists()

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    def fake_rmtree(path):  # noqa: ARG001
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1

    out, err = capfd.readouterr()
    assert f"Clearing cache directory: {fake_cache_dir}" in out
    assert "Error clearing cache:" in err
