#!/usr/bin/env python3

import logging
from itertools import groupby
from pathlib import Path
from typing import List

import click
import requests
import rich
import toml
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel.extra import InlineArrayDictEncoder
from cibuildwheel.typing import Final, PlatformName, TypedDict

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"

CIBW_SUPPORTED_PYTHONS: Final[SpecifierSet] = SpecifierSet(">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*")


class AnyConfig(TypedDict):
    identifier: str
    version: Version


class ConfigWinCP(AnyConfig):
    arch: str


class ConfigWinPP(AnyConfig):
    arch: str
    url: str


class ConfigMacOS(AnyConfig):
    url: str


def get_cpython_windows() -> List[ConfigWinCP]:
    log.info("[bold]Collecting Windows CPython from nuget")
    ARCH_DICT = {"32": "win32", "64": "win_amd64"}

    response = requests.get("https://api.nuget.org/v3/index.json")
    response.raise_for_status()
    api_info = response.json()

    for resource in api_info["resources"]:
        if resource["@type"] == "PackageBaseAddress/3.0.0":
            endpoint = resource["@id"]

    items: List[ConfigWinCP] = []

    for arch, package in [("64", "python"), ("32", "pythonx86")]:
        response = requests.get(f"{endpoint}{package}/index.json")
        response.raise_for_status()
        cp_info = response.json()

        for version_str in cp_info["versions"]:
            version = Version(version_str)

            if version.is_devrelease:
                continue

            identifier = f"cp{version.major}{version.minor}-{ARCH_DICT[arch]}"

            items.append(
                ConfigWinCP(
                    identifier=identifier,
                    version=version,
                    arch=arch,
                )
            )
            log.debug(items[-1])
    return items


def get_pypy(platform: PlatformName) -> List[AnyConfig]:
    log.info("[bold]Collecting PyPy from python.org")

    response = requests.get("https://downloads.python.org/pypy/versions.json")
    response.raise_for_status()
    pp_releases = response.json()

    items: List[AnyConfig] = []

    for pp_release in pp_releases:

        if pp_release["pypy_version"] == "nightly":
            continue
        pypy_version = Version(pp_release["pypy_version"])
        if pypy_version.is_prerelease or pypy_version.is_devrelease:
            continue

        version = Version(pp_release["python_version"])

        for rf in pp_release["files"]:
            if platform == "windows":
                if rf["platform"] == "win32" and rf["arch"] == "x86":
                    identifier = f"pp{version.major}{version.minor}-win32"
                    items.append(
                        ConfigWinPP(
                            identifier=identifier,
                            version=Version(f"{version.major}.{version.minor}"),
                            arch="32",
                            url=rf["download_url"],
                        )
                    )
                    log.debug(items[-1])
                    break
            elif platform == "macos":
                if rf["platform"] == "darwin" and rf["arch"] == "x64":
                    identifier = f"pp{version.major}{version.minor}-macosx_x86_64"
                    items.append(
                        ConfigMacOS(
                            identifier=identifier,
                            version=Version(f"{version.major}.{version.minor}"),
                            url=rf["download_url"],
                        )
                    )
                    log.debug(items[-1])
                    break

    return items


def _get_id(resource_uri: str) -> int:
    return int(resource_uri.rstrip("/").split("/")[-1])


def get_cpython(
    plat_arch: str,
    file_ident: str,
    versions: SpecifierSet = CIBW_SUPPORTED_PYTHONS,
) -> List[ConfigMacOS]:
    log.info(f"[bold]Collecting {plat_arch} CPython from Python.org")

    response = requests.get("https://www.python.org/api/v2/downloads/release/?is_published=true")
    response.raise_for_status()

    releases_info = response.json()
    # Removing the prefix, Python 3.9 would use: release["name"].removeprefix("Python ")
    known_versions = {Version(release["name"][7:]): _get_id(release["resource_uri"]) for release in releases_info}

    items: List[ConfigMacOS] = []

    sorted_versions = sorted((v for v in known_versions if versions.contains(v) and not v.is_prerelease), reverse=True)
    # Group is a list of sorted patch versions
    for pair, group in groupby(sorted_versions, lambda x: (x.major, x.minor)):
        log.info(f"[bold]Working on {pair[0]}.{pair[1]}")
        # Find the first patch version that contains the requested file
        for version in group:
            uri = known_versions[version]

            log.info(f"  Checking {version}")
            response = requests.get(f"https://www.python.org/api/v2/downloads/release_file/?release={uri}")
            response.raise_for_status()
            file_info = response.json()

            canidate_files = [rf["url"] for rf in file_info if file_ident in rf["url"]]
            if canidate_files:
                items.append(
                    ConfigMacOS(
                        identifier=f"cp{version.major}{version.minor}-{plat_arch}",
                        version=version,
                        url=canidate_files[0],
                    )
                )
                log.info("[green]  Found!")
                break
    return items


def sort_and_filter_configs(
    orig_items: List[AnyConfig],
    *,
    prereleases: bool = False,
) -> List[AnyConfig]:

    items: List[AnyConfig] = []

    # Groupby requires pre-grouped input
    orig_items = sorted(orig_items, key=lambda x: x["identifier"])

    for _, grp in groupby(orig_items, lambda x: x["identifier"]):
        # Never select dev releases
        choices = list(filter(lambda x: not x["version"].is_devrelease, grp))

        # Filter pre-releases, unless it's all pre-releases
        if not all(x["version"].is_prerelease for x in grp):
            choices = list(filter(lambda x: not x["version"].is_prerelease, choices))

        # Select the highest choice unless there are none
        _url = "url"  # Needed for MyPy, see https://github.com/python/mypy/issues/9902
        choices = sorted(choices, key=lambda x: (x["version"], x.get(_url)))
        if not choices:
            continue
        best_choice = choices[-1]

        # Only allow a pre-release if they are all prereleases, and we've asked for them
        if best_choice["version"].is_prerelease and not prereleases:
            continue

        items.append(best_choice)

    return sorted(
        items,
        key=lambda x: (
            x["identifier"][:3],
            x["version"].minor,
            x["identifier"].split("-")[-1],
        ),
    )


CLASSIC_WINDOWS: List[ConfigWinCP] = [
    {"identifier": "cp27-win32", "version": Version("2.7.18"), "arch": "32"},
    {"identifier": "cp27-win_amd64", "version": Version("2.7.18"), "arch": "64"},
]


@click.command()
@click.option("--inplace", is_flag=True)
@click.option("--prereleases", is_flag=True)
@click.option("--level", default="INFO", type=click.Choice(["INFO", "DEBUG", "TRACE"], case_sensitive=False))
def update_pythons(inplace: bool, prereleases: bool, level: str) -> None:

    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    log.setLevel(level)

    windows_configs: List[AnyConfig] = [
        *CLASSIC_WINDOWS,
        *get_cpython_windows(),
        *get_pypy("windows"),
    ]

    windows_configs = sort_and_filter_configs(
        windows_configs,
        prereleases=prereleases,
    )

    macos_configs = [
        *get_cpython(
            plat_arch="macosx_x86_64",
            file_ident="macosx10.9.pkg",
        ),
        *get_cpython(
            plat_arch="macosx_x86_64",
            file_ident="macosx10.6.pkg",
            versions=SpecifierSet("==3.5.*"),
        ),
        *get_pypy("macos"),
    ]

    # For universal2:
    #     plat_arch="macosx_universal2",
    #     file_ident="macos11.0.pkg",
    #     versions=SpecifierSet(">=3.8"),

    macos_configs = sort_and_filter_configs(
        macos_configs,
        prereleases=prereleases,
    )

    for config in macos_configs:
        config["version"] = Version("{0.major}.{0.minor}".format(config["version"]))

    configs = toml.load(RESOURCES_DIR / "build-platforms.toml")
    configs["windows"]["python_configurations"] = windows_configs
    configs["macos"]["python_configurations"] = macos_configs

    if inplace:
        with open(RESOURCES_DIR / "build-platforms.toml", "w") as f:
            toml.dump(configs, f, encoder=InlineArrayDictEncoder())  # type: ignore
    else:
        output = toml.dumps(configs, encoder=InlineArrayDictEncoder())  # type: ignore
        rich.print(Syntax(output, "toml", theme="ansi_light"))
        log.info("File not changed, use --inplace flag to update.")


if __name__ == "__main__":
    update_pythons()
