import sys
import os
import subprocess

import pytest

from main_function_test_utils import argtest, apply_mock_protection
from cibuildwheel.__main__ import main

def test_unknown_platform_non_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {})
    apply_mock_protection(monkeypatch)
    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 2
    _, err = capsys.readouterr()
    assert 'cibuildwheel: Unable to detect platform.' in err
    assert "cibuildwheel should run on your CI server" in err


def test_unknown_platform_on_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {"CI": "true"})
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(sys, "platform", "Something")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {"CIBW_PLATFORM": "Something"})
    apply_mock_protection(monkeypatch)
    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unsupported platform: Something' in err