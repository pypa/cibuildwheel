import pytest

from cibuildwheel.logger import BuildInfo, Logger


def test_printout_wheels(capsys):
    log = Logger()
    log.fold_mode = "disabled"
    log.colors_enabled = False
    log.summary_mode = "generic"

    with log.print_summary():
        log.summary = [
            BuildInfo(identifier="id1", filename=None, duration=3),
            BuildInfo(identifier="id2", filename=None, duration=2),
        ]

    captured = capsys.readouterr()
    assert captured.err == ""

    assert "id1" in captured.out
    assert "id2" in captured.out
    assert "wheels produced in" in captured.out


def test_no_printout_on_error(capsys):
    log = Logger()
    with pytest.raises(RuntimeError), log.print_summary():
        raise RuntimeError()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""
