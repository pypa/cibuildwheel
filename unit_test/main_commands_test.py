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

    cibw_sentinel = fake_cache_dir / "CACHEDIR.TAG"
    cibw_sentinel.write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
        "# This file is a cache directory tag created by cibuildwheel.\n"
        "# For information about cache directory tags, see:\n"
        "# https://www.brynosaurus.com/cachedir/",
        encoding="utf-8",
    )

    dummy_file = fake_cache_dir / "dummy.txt"
    dummy_file.write_text("hello")

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 0

    out, _ = capfd.readouterr()
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

    out, _ = capfd.readouterr()
    assert f"Cache directory does not exist: {fake_cache_dir}" in out


def test_clean_cache_with_error(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "cibw_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    fake_cache_dir.mkdir(parents=True, exist_ok=True)
    assert fake_cache_dir.exists()

    cibw_sentinel = fake_cache_dir / "CACHEDIR.TAG"
    cibw_sentinel.write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
        "# This file is a cache directory tag created by cibuildwheel.\n"
        "# For information about cache directory tags, see:\n"
        "# https://www.brynosaurus.com/cachedir/",
        encoding="utf-8",
    )

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


def test_clean_cache_without_sentinel(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "not_a_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    fake_cache_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1

    _, err = capfd.readouterr()
    assert "does not appear to be a cibuildwheel cache directory" in err
    assert fake_cache_dir.exists()


def test_clean_cache_with_invalid_signature(tmp_path, monkeypatch, capfd):
    fake_cache_dir = (tmp_path / "fake_cache").resolve()
    monkeypatch.setattr(main_module, "CIBW_CACHE_PATH", fake_cache_dir)

    fake_cache_dir.mkdir(parents=True, exist_ok=True)

    cibw_sentinel = fake_cache_dir / "CACHEDIR.TAG"
    cibw_sentinel.write_text("Invalid signature\n# This is not a real cache directory tag")

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--clean-cache"])

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1

    _, err = capfd.readouterr()
    assert "does not contain a valid cache directory signature" in err
    assert fake_cache_dir.exists()
