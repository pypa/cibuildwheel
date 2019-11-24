import sys
import os
import subprocess

import pytest

from cibuildwheel.__main__ import main
from cibuildwheel import windows, linux, macos


def not_call_mock(*args, **kwargs):
    raise RuntimeError("This should never be called")


def apply_mock_protection(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", not_call_mock)
    monkeypatch.setattr(windows, "urlopen", not_call_mock)
    monkeypatch.setattr(windows, "build", not_call_mock)
    monkeypatch.setattr(linux, "build", not_call_mock)
    monkeypatch.setattr(macos, "build", not_call_mock)


def test_unknown_platform_non_ci(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(os, 'environ', {})
    monkeypatch.setattr(sys, "argv", ["python", str(tmp_path)])
    apply_mock_protection(monkeypatch)
    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 2
    _, err = capsys.readouterr()
    assert 'cibuildwheel: Unable to detect platform.' in err
    assert "cibuildwheel should run on your CI server" in err


def test_unknown_platform_on_ci(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(os, 'environ', {"CI": "true"})
    monkeypatch.setattr(sys, "argv", ["python", str(tmp_path)])
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(sys, "platform", "Something")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(os, 'environ', {"CIBW_PLATFORM": "Something"})
    monkeypatch.setattr(sys, "argv", ["python", str(tmp_path)])
    apply_mock_protection(monkeypatch)
    with open(str(tmp_path / "setup.py"), "w") as f:
        f.write('from setuptools import setup\nsetup(name="spam", version="0.1.0",)')

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unsupported platform: Something' in err
