#!/usr/bin/env python3

from itertools import groupby
from pathlib import Path
from typing import List

import click
import requests
import toml
from packaging.version import Version

from cibuildwheel.extra import InlineArrayDictEncoder
from cibuildwheel.typing import PlatformName, TypedDict

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR = Path(__file__).parent.parent.resolve()
RESOURCES_DIR = DIR / "cibuildwheel/resources"


class AnyConfig(TypedDict):
    identifier: str
    version: Version


class ConfigWinCP(AnyConfig):
    arch: str


class ConfigWinPP(AnyConfig):
    arch: str
    url: str


def get_cpython_windows() -> List[ConfigWinCP]:
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
    return items


def get_pypy(platform: PlatformName) -> List[AnyConfig]:

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
@click.option("--all", is_flag=True)
def update_pythons(inplace: bool, prereleases: bool, all: bool) -> None:
    windows_configs: List[AnyConfig] = [
        *CLASSIC_WINDOWS,
        *get_cpython_windows(),
        *get_pypy("windows"),
    ]

    if not all:
        windows_configs = sort_and_filter_configs(
            windows_configs,
            prereleases=prereleases,
        )

    configs = toml.load(RESOURCES_DIR / "build-platforms.toml")
    configs["windows"]["python_configurations"] = windows_configs

    if inplace:
        with open(RESOURCES_DIR / "build-platforms.toml", "w") as f:
            toml.dump(configs, f, encoder=InlineArrayDictEncoder())  # type: ignore
    else:
        print(toml.dumps(configs, encoder=InlineArrayDictEncoder()))  # type: ignore


if __name__ == "__main__":
    update_pythons()
