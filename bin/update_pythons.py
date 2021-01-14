#!/usr/bin/env python3

import logging
from itertools import groupby
from pathlib import Path
from typing import Dict, List, Optional

import click
import requests
import rich
import tomlkit
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel.extra import InlineArrayDictEncoder
from cibuildwheel.typing import Final, Literal, PlatformName, TypedDict

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"

CIBW_SUPPORTED_PYTHONS: Final[SpecifierSet] = SpecifierSet(">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*")


ArchStr = Literal["32", "64"]


class ConfigWinCP(TypedDict):
    identifier: str
    version: Version
    arch: str


class ConfigWinPP(TypedDict):
    identifier: str
    version: Version
    arch: str
    url: str


class ConfigMacOS(TypedDict):
    identifier: str
    version: Version
    url: str


AnyConfig = Union[ConfigWinCP, ConfigWinPP, ConfigMacOS]


class WindowsVersions:
    def __init__(self, arch_str: ArchStr) -> None:

        response = requests.get("https://api.nuget.org/v3/index.json")
        response.raise_for_status()
        api_info = response.json()

        for resource in api_info["resources"]:
            if resource["@type"] == "PackageBaseAddress/3.0.0":
                endpoint = resource["@id"]

        ARCH_DICT = {"32": "win32", "64": "win_amd64"}
        PACKAGE_DICT = {"32": "pythonx86", "64": "python"}

        arch = ARCH_DICT[arch_str]
        package = PACKAGE_DICT[arch_str]

        response = requests.get(f"{endpoint}{package}/index.json")
        response.raise_for_status()
        cp_info = response.json()

        versions = (Version(v) for v in cp_info["versions"])
        self.versions = sorted(v for v in versions if not v.is_devrelease)

    def update_version(self, spec: Specifier) -> Optional[ConfigWinCP]:
        versions = sorted(v for v in self.versions if spec.contains(v))
        if not all(v.is_prerelease for v in versions):
            versions = [v for v in versions if not v.is_prerelease]
        log.debug(versions)

        if not versions:
            return None

        version = versions[-1]
        identifier = f"cp{version.major}{version.minor}-{ARCH_DICT[arch]}"
        result = ConfigWinCP(
            identifier=identifier,
            version=version,
            arch=arch,
        )
        return result


class PyPyVersions:
    def __init__(self, arch_str: ArchStr):

        response = requests.get("https://downloads.python.org/pypy/versions.json")
        response.raise_for_status()

        releases = [r for r in response.json() if r["pypy_version"] != "nightly"]
        for release in releases:
            release["pypy_version"] = Version(release["pypy_version"])
            release["python_version"] = Version(release["python_version"])

        self.releases = [r for r in releases if not r["pypy_version"].is_prerelease and r["pypy_version"].is_devrelease]
        self.arch == arch_str

    def update_version_windows(self, spec: Specifier) -> Optional[ConfigWinCP]:
        if self.arch != "32":
            raise RuntimeError("64 bit releases not supported yet on Windows")

        releases = [r for r in releases if spec.contains(r["python_verison"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])

        if not releases:
            return None

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-win32"
        return ConfigWinPP(
            identifier=identifier,
            version=Version(f"{version.major}.{version.minor}"),
            arch="32",
            url=r["download_url"],
        )

    def update_version_macos(self, spec: Specifier) -> Optional[ConfigMacOS]:
        if self.arch != "64":
            raise RuntimeError("Other archs not supported yet on macOS")

        releases = [r for r in releases if spec.contains(r["python_verison"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])

        if not releases:
            return None

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-win32"

        return ConfigMacOS(
            identifier=identifier,
            version=Version(f"{version.major}.{version.minor}"),
            url=rf["download_url"],
        )


def _get_id(resource_uri: str) -> int:
    return int(resource_uri.rstrip("/").split("/")[-1])


class CPythonVersions:
    def __init__(self, plat_arch: str, file_ident: str) -> None:

        response = requests.get("https://www.python.org/api/v2/downloads/release/?is_published=true")
        response.raise_for_status()

        releases_info = response.json()

        # Removing the prefix, Python 3.9 would use: release["name"].removeprefix("Python ")
        known_versions = {Version(release["name"][7:]): _get_id(release["resource_uri"]) for release in releases_info}
        self.versions = sorted(v for v in known_versions if not (v.is_prerelease or v.is_devrelease))

    def update_python_macos(self, spec: Specifier) -> Optional[ConfigMacOS]:

        sorted_versions = [v for v in self.versions if spec.contains(v)]

        for version in reversed(versions):
            # Find the first patch version that contains the requested file
            uri = self.versions[version]
            response = requests.get(f"https://www.python.org/api/v2/downloads/release_file/?release={uri}")
            response.raise_for_status()
            file_info = response.json()

            canidate_files = [rf["url"] for rf in file_info if file_ident in rf["url"]]
            if canidate_files:
                return ConfigMacOS(
                    identifier=f"cp{version.major}{version.minor}-{plat_arch}",
                    version=version,
                    url=canidate_files[0],
                )

        return None


@click.command()
@click.option("--inplace", is_flag=True)
@click.option("--level", default="INFO", type=click.Choice(["INFO", "DEBUG", "TRACE"], case_sensitive=False))
def update_pythons(inplace: bool, prereleases: bool, level: str) -> None:

    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    log.setLevel(level)

    windows_32 = WindowsVersions("32")
    windows_64 = WindowsVersions("64")
    windows_pypy = PyPyVersions("32")

    macos_6 = CPythonVersions(plat_arch="macosx_x86_64", file_ident="macosx10.6.pkg")

    macos_9 = CPythonVersions(plat_arch="macosx_x86_64", file_ident="macosx10.9.pkg")

    macos_u2 = CPythonVersions(
        plat_arch="macosx_universal2",
        file_ident="macos11.0.pkg",
    )

    macos_pypy = PyPyVersions("64")

    configs = toml.load(RESOURCES_DIR / "build-platforms.toml")

    for config in configs["windows"]["python_configurations"]:
        version = Version(config["version"])
        spec = Specifier(f"=={version.major}.{version.minor}.*")
        arch = config["arch"]
        cpython = config["identifier"].startswith("cp")

    for config in configs["macos"]["python_configurations"]:
        version = Version(config["version"])
        spec = Specifier(f"=={version.major}.{version.minor}.*")
        arch = "64"
        pypy = config["identifier"].startswith("pp")

    if inplace:
        with open(RESOURCES_DIR / "build-platforms.toml", "w") as f:
            toml.dump(configs, f, encoder=InlineArrayDictEncoder())  # type: ignore
    else:
        output = toml.dumps(configs, encoder=InlineArrayDictEncoder())  # type: ignore
        rich.print(Syntax(output, "toml", theme="ansi_light"))
        log.info("File not changed, use --inplace flag to update.")


if __name__ == "__main__":
    update_pythons()
