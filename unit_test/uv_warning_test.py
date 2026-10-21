from __future__ import annotations

from pathlib import Path

import pytest

import cibuildwheel.__main__
from cibuildwheel.__main__ import detect_uv_warnings
from cibuildwheel.options import CommandLineArguments, Options

TYPE_CHECKING = False
if TYPE_CHECKING:
    from cibuildwheel.typing import PlatformName


@pytest.mark.parametrize(
    ("platform", "frontend", "expected"),
    [
        ("macos", "uv", True),
        ("windows", "build[uv]", True),
        ("macos", "build", False),
        ("linux", "uv", False),
    ],
)
def test_detect_uv_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform: PlatformName,
    frontend: str,
    *,
    expected: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cibuildwheel.__main__, "find_uv", lambda: Path("uv"))
    monkeypatch.setattr(cibuildwheel.__main__, "uv_ca_warning", lambda _: "old uv")

    args = CommandLineArguments.defaults()
    options = Options(platform, command_line_arguments=args, env={"CIBW_BUILD_FRONTEND": frontend})

    warnings = list(
        detect_uv_warnings(platform=platform, options=options, identifiers=["cp313-any"])
    )
    assert warnings == (["old uv"] if expected else [])
