#!/usr/bin/env python3


import dataclasses
import difflib
import logging
import subprocess
import tomllib
from pathlib import Path
from typing import Final

import click
import rich
from packaging.version import InvalidVersion, Version
from rich.logging import RichHandler
from rich.syntax import Syntax

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"

GET_VIRTUALENV_GITHUB: Final[str] = "https://github.com/pypa/get-virtualenv"
GET_VIRTUALENV_URL_TEMPLATE: Final[str] = (
    f"{GET_VIRTUALENV_GITHUB}/blob/{{version}}/public/virtualenv.pyz?raw=true"
)


@dataclasses.dataclass(frozen=True, order=True)
class VersionTuple:
    version: Version
    version_string: str


def git_ls_remote_versions(url: str) -> list[VersionTuple]:
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
        configurations = tomllib.load(f)
    default = configurations.pop("default")
    version = str(default["version"])
    versions = git_ls_remote_versions(GET_VIRTUALENV_GITHUB)
    if versions[0].version > Version(version):
        version = versions[0].version_string

    configurations["default"] = {
        "version": version,
        "url": GET_VIRTUALENV_URL_TEMPLATE.format(version=version),
    }
    result_toml = "".join(
        f'{key} = {{ version = "{value["version"]}", url = "{value["url"]}" }}\n'
        for key, value in configurations.items()
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
