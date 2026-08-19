from pathlib import Path

import pytest

from cibuildwheel.ci import CIProvider
from cibuildwheel.logger import BuildInfo, Logger
from cibuildwheel.options import CommandLineArguments, Options

OPTIONS_DEFAULTS = Options("linux", CommandLineArguments.defaults(), {}, defaults=True)
FILE = Path(__file__)


@pytest.mark.parametrize("fold_mode", ["azure", "github", "travis", "disabled"])
def test_log_fold_mode_environment_override(
    monkeypatch: pytest.MonkeyPatch, fold_mode: str
) -> None:
    monkeypatch.setenv("CIBW_LOG_FOLD_MODE", fold_mode)
    monkeypatch.setattr(
        "cibuildwheel.logger.detect_ci_provider",
        lambda: CIProvider.github_actions,
    )

    assert Logger().fold_mode == fold_mode


def test_invalid_log_fold_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIBW_LOG_FOLD_MODE", "unknown")

    with pytest.raises(ValueError, match="CIBW_LOG_FOLD_MODE must be one of"):
        Logger()


def test_printout_wheels(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_no_printout_on_error(capsys: pytest.CaptureFixture[str]) -> None:
    log = Logger()
    with pytest.raises(RuntimeError), log.print_summary(options=OPTIONS_DEFAULTS):
        raise RuntimeError()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""
