from __future__ import annotations

from pathlib import Path

from cibuildwheel.options import CommandLineArguments, Options
from cibuildwheel.platforms import android

TYPE_CHECKING = False
if TYPE_CHECKING:
    import pytest


def test_uv_build_uses_build_venv_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # without --python, uv build follows the project's .python-version, not the build venv
    identifier = "cp314-android_arm64_v8a"
    args = CommandLineArguments.defaults()
    args.package_dir = tmp_path
    options = Options(
        platform="android", command_line_arguments=args, env={"CIBW_BUILD_FRONTEND": "uv"}
    )
    build_path = tmp_path / identifier
    calls: list[tuple[object, ...]] = []

    def fake_call(*args: object, **_: object) -> None:
        calls.append(args)
        wheel_dir = build_path / "built_wheel"
        wheel_dir.mkdir(parents=True)
        (wheel_dir / "pkg-0.1-cp314-cp314-android_24_arm64_v8a.whl").touch()

    monkeypatch.setattr(android, "find_uv", lambda: Path("uv"))
    monkeypatch.setattr(android, "call", fake_call)

    state = android.BuildState(
        config=android.PythonConfiguration("3.14", identifier, url="", sha256=""),
        options=options.build_options(identifier),
        build_path=build_path,
        python_dir=build_path / "python",
        build_env={},
        android_env={},
    )
    android.build_wheel(state)

    (uv_args,) = calls
    venv_python = build_path / "venv" / "bin" / "python"
    assert uv_args[:3] == (Path("uv"), "build", f"--python={venv_python}")
