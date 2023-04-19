#!/usr/bin/env python3

from __future__ import annotations

import difflib
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import click
import rich

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.version import InvalidVersion, Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel._compat.typing import Final

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"

GET_VIRTUALENV_GITHUB: Final[str] = "https://github.com/pypa/get-virtualenv"
GET_VIRTUALENV_URL_TEMPLATE: Final[
    str
] = f"{GET_VIRTUALENV_GITHUB}/blob/{{version}}/public/virtualenv.pyz?raw=true"


@dataclass(frozen=True, order=True)
class VersionTuple:
    version: Version
    version_string: str


def git_ls_remote_versions(url) -> list[VersionTuple]:
    versions: list[VersionTuple] = []
    tags = subprocess.run(
        ["git", "ls-remote", "--tags", url], check=True, text=True, capture_output=True
    ).stdout.splitlines()
    for tag in tags:
        _, ref = tag.split()
        assert ref.startswith("refs/tags/")
        version_string = ref[10:]
        try:
            version = Version(version_string)
            if version.is_devrelease:
                log.info("Ignoring development release %r", str(version))
                continue
            if version.is_prerelease:
                log.info("Ignoring pre-release %r", str(version))
                continue
            versions.append(VersionTuple(version, version_string))
        except InvalidVersion:
            log.warning("Ignoring ref %r", ref)
    versions.sort(reverse=True)
    return versions


@click.command()
@click.option("--force", is_flag=True)
@click.option(
    "--level", default="INFO", type=click.Choice(["WARNING", "INFO", "DEBUG"], case_sensitive=False)
)
def update_virtualenv(force: bool, level: str) -> None:
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    log.setLevel(level)

    toml_file_path = RESOURCES_DIR / "virtualenv.toml"

    original_toml = toml_file_path.read_text()
    with toml_file_path.open("rb") as f:
        loaded_file = tomllib.load(f)
    version = str(loaded_file["version"])
    versions = git_ls_remote_versions(GET_VIRTUALENV_GITHUB)
    if versions[0].version > Version(version):
        version = versions[0].version_string

    result_toml = (
        f'version = "{version}"\n'
        f'url = "{GET_VIRTUALENV_URL_TEMPLATE.format(version=version)}"\n'
    )

    rich.print()  # spacer

    if original_toml == result_toml:
        rich.print("[green]Check complete, virtualenv version unchanged.")
        return

    rich.print("virtualenv version updated.")
    rich.print("Changes:")
    rich.print()

    toml_relpath = toml_file_path.relative_to(DIR).as_posix()
    diff_lines = difflib.unified_diff(
        original_toml.splitlines(keepends=True),
        result_toml.splitlines(keepends=True),
        fromfile=toml_relpath,
        tofile=toml_relpath,
    )
    rich.print(Syntax("".join(diff_lines), "diff", theme="ansi_light"))
    rich.print()

    if force:
        toml_file_path.write_text(result_toml)
        rich.print("[green]TOML file updated.")
    else:
        rich.print("[yellow]File left unchanged. Use --force flag to update.")


if __name__ == "__main__":
    update_virtualenv()
