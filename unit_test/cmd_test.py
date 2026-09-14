from __future__ import annotations

import subprocess
import sys

import pytest

from cibuildwheel.util.cmd import call

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "value",
    [
        "hello world",
        "a&b",
        "a|b",
        "100%PATH%",
        "caret^char",
        "package[extra]<5,>=4",
    ],
)
def test_call_preserves_cmd_metacharacters(value: str) -> None:
    # Regression: call() used shell=True on Windows, so cmd.exe treated & / |
    # as command separators and expanded %VAR%. After resolving the executable
    # with shutil.which, the child must receive the argument intact.
    out = call(
        sys.executable,
        "-c",
        "import sys; print(sys.argv[1], end='')",
        value,
        capture_stdout=True,
    )
    assert out == value


def test_call_preserves_path_with_spaces(tmp_path: Path) -> None:
    spaced = tmp_path / "path with spaces"
    spaced.mkdir()
    marker = spaced / "out.txt"
    call(
        sys.executable,
        "-c",
        "import sys; open(sys.argv[1], 'w', encoding='utf-8').write('ok')",
        str(marker),
    )
    assert marker.read_text(encoding="utf-8") == "ok"


def test_call_does_not_use_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["args"] = args
        recorded["shell"] = kwargs.get("shell", False)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    call(sys.executable, "-c", "pass")
    assert recorded["shell"] is False
    assert isinstance(recorded["args"], list)
