from pathlib import Path

import pytest

from cibuildwheel.logger import BuildInfo, Logger
from cibuildwheel.options import CommandLineArguments, Options

OPTIONS_DEFAULTS = Options("linux", CommandLineArguments.defaults(), {}, defaults=True)
FILE = Path(__file__)


def test_printout_wheels(capsys):
    log = Logger()
    log.fold_mode = "disabled"
    log.colors_enabled = False

    with log.print_summary(options=OPTIONS_DEFAULTS):
        # the number of BuildInfo with & without filename shall be different for this test
        log.summary = [
            BuildInfo(identifier="id1", filename=None, duration=3),
            BuildInfo(identifier="id2", filename=FILE, duration=2),
            BuildInfo(identifier="id3", filename=FILE, duration=3),
        ]

    captured = capsys.readouterr()
    assert captured.err == ""

    assert "id1" in captured.out
    assert "id2" in captured.out
    assert "id3" in captured.out
    assert "2 wheels produced in" in captured.out
    assert "SHA256=" in captured.out


def test_no_printout_on_error(capsys):
    log = Logger()
    with pytest.raises(RuntimeError), log.print_summary(options=OPTIONS_DEFAULTS):
        raise RuntimeError()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""
