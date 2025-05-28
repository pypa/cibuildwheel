#!/usr/bin/env python3


import dataclasses
import difflib
import logging
import tomllib
from pathlib import Path
from typing import Final

import click
import packaging.specifiers
import requests
import rich
from packaging.version import InvalidVersion, Version
from rich.logging import RichHandler
from rich.syntax import Syntax

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"

NODEJS_DIST: Final[str] = "https://nodejs.org/dist/"
NODEJS_INDEX: Final[str] = f"{NODEJS_DIST}index.json"


@dataclasses.dataclass(frozen=True, order=True)
class VersionTuple:
    version: Version
    version_string: str


def parse_nodejs_index() -> list[VersionTuple]:
    versions: list[VersionTuple] = []
    response = requests.get(NODEJS_INDEX)
    response.raise_for_status()
    versions_info = response.json()
    for version_info in versions_info:
        version_string = version_info.get("version", "???")
        if not version_info.get("lts", False):
            log.debug("Ignoring non LTS release %r", version_string)
            continue
        if "linux-x64" not in version_info.get("files", []):
            log.warning(
                "Ignoring release %r which does not include a linux-x64 binary", version_string
            )
            continue
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
            log.warning("Ignoring release %r", version_string)
    versions.sort(reverse=True)
    return versions


@click.command()
@click.option("--force", is_flag=True)
@click.option(
    "--level", default="INFO", type=click.Choice(["WARNING", "INFO", "DEBUG"], case_sensitive=False)
)
def update_nodejs(force: bool, level: str) -> None:
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    log.setLevel(level)

    toml_file_path = RESOURCES_DIR / "nodejs.toml"

    original_toml = toml_file_path.read_text()
    with toml_file_path.open("rb") as f:
        nodejs_data = tomllib.load(f)

    nodejs_data.pop("url")

    major_versions = [VersionTuple(Version(key), key) for key in nodejs_data]
    major_versions.sort(reverse=True)

    versions = parse_nodejs_index()

    # update existing versions, 1 per LTS
    for major_version in major_versions:
        current = Version(nodejs_data[major_version.version_string])
        specifier = packaging.specifiers.SpecifierSet(
            specifiers=f"=={major_version.version.major}.*"
        )
        for version in versions:
            if specifier.contains(version.version) and version.version > current:
                nodejs_data[major_version.version_string] = version.version_string
                break

    # check for a new major LTS to insert
    if versions and versions[0].version.major > major_versions[0].version.major:
        major_versions.insert(
            0,
            VersionTuple(Version(str(versions[0].version.major)), f"v{versions[0].version.major}"),
        )
        nodejs_data[major_versions[0].version_string] = versions[0].version_string

    versions_toml = "\n".join(
        f'{major_version.version_string} = "{nodejs_data[major_version.version_string]}"'
        for major_version in major_versions
    )
    result_toml = f'url = "{NODEJS_DIST}"\n{versions_toml}\n'

    rich.print()  # spacer

    if original_toml == result_toml:
        rich.print("[green]Check complete, nodejs version unchanged.")
        return

    rich.print("nodejs version updated.")
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
    update_nodejs()
