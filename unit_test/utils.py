from __future__ import annotations

from pathlib import Path

from cibuildwheel.options import CommandLineArguments


def get_default_command_line_arguments() -> CommandLineArguments:
    defaults = CommandLineArguments(
        platform="auto",
        allow_empty=False,
        archs=None,
        only=None,
        config_file="",
        output_dir=Path("wheelhouse"),
        package_dir=Path("."),
        prerelease_pythons=False,
        print_build_identifiers=False,
    )

    return defaults
