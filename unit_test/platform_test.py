import sys
import os

import pytest

from cibuildwheel.__main__ import main


def test_unknown_platform_non_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {})
    monkeypatch.setattr(sys, "argv", ["python", "."])
    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 2
    _, err = capsys.readouterr()
    assert 'cibuildwheel: Unable to detect platform.' in err
    assert "cibuildwheel should run on your CI server" in err


def test_unknown_platform_on_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {"CI": "true"})
    monkeypatch.setattr(sys, "argv", ["python", "."])

    monkeypatch.setattr(sys, "platform", "Something")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch):
    monkeypatch.setattr(os, 'environ', {"CIBW_PLATFORM": "Something"})
    monkeypatch.setattr(sys, "argv", ["python", "."])

    with pytest.raises(Exception) as exc:
        main()
    assert exc.value.args[0] == 'Unsupported platform: Something'
