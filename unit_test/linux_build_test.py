from __future__ import annotations

import pytest

from cibuildwheel.errors import ConfigurationError
from cibuildwheel.options import CommandLineArguments, Options
from cibuildwheel.platforms.linux import build

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path


def test_package_dir_outside_working_directory_raises_fatal_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    package_dir.joinpath("pyproject.toml").touch()

    monkeypatch.chdir(work_dir)

    command_line_arguments = CommandLineArguments.defaults()
    command_line_arguments.package_dir = package_dir
    options = Options(platform="linux", command_line_arguments=command_line_arguments, env={})

    with pytest.raises(
        ConfigurationError, match="package_dir must be inside the working directory"
    ):
        build(options, tmp_path / "build")
