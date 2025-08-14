#!/usr/bin/env python3


import dataclasses
import difflib
import logging
import tomllib
from pathlib import Path
from typing import Final

import click
import rich
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel.extra import github_api_request

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
    name: str
    download_url: str
    version: Version


def get_latest_virtualenv_release() -> VersionTuple:
    response = github_api_request("repos/pypa/get-virtualenv/releases/latest")
    tag_name = response["tag_name"]

    asset = next(
        (asset for asset in response["assets"] if asset["name"] == "virtualenv.pyz"),
        None,
    )
    if not asset:
        msg = "No asset named 'virtualenv.pyz' found in the latest release of get-virtualenv."
        raise RuntimeError(msg)

    return VersionTuple(
        version=Version(tag_name), name=tag_name, download_url=asset["browser_download_url"]
    )


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
    local_version = str(default["version"])

    latest_release = get_latest_virtualenv_release()

    if latest_release.version > Version(local_version):
        version = latest_release.name
        url = latest_release.download_url
    else:
        version = local_version
        url = default["url"]

    configurations["default"] = {
        "version": version,
        "url": url,
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
