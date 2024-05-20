#!/usr/bin/env python3

from __future__ import annotations

import copy
import difflib
import logging
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, Final, Literal, TypedDict, Union

import click
import requests
import rich
from packaging.specifiers import Specifier
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel._compat import tomllib
from cibuildwheel.extra import dump_python_configurations

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"


ArchStr = Literal["32", "64", "ARM64"]


class ConfigWinCP(TypedDict):
    identifier: str
    version: str
    arch: str


class ConfigWinPP(TypedDict):
    identifier: str
    version: str
    arch: str
    url: str


class ConfigMacOS(TypedDict):
    identifier: str
    version: str
    url: str


AnyConfig = Union[ConfigWinCP, ConfigWinPP, ConfigMacOS]


# The following set of "Versions" classes allow the initial call to the APIs to
# be cached and reused in the `update_version_*` methods.


class WindowsVersions:
    def __init__(self, arch_str: ArchStr, free_threaded: bool) -> None:
        response = requests.get("https://api.nuget.org/v3/index.json")
        response.raise_for_status()
        api_info = response.json()

        for resource in api_info["resources"]:
            if resource["@type"] == "PackageBaseAddress/3.0.0":
                endpoint = resource["@id"]

        ARCH_DICT = {"32": "win32", "64": "win_amd64", "ARM64": "win_arm64"}
        PACKAGE_DICT = {"32": "pythonx86", "64": "python", "ARM64": "pythonarm64"}

        self.arch_str = arch_str
        self.arch = ARCH_DICT[arch_str]
        self.free_threaded = free_threaded

        package = PACKAGE_DICT[arch_str]
        if free_threaded:
            package = f"{package}-freethreaded"

        response = requests.get(f"{endpoint}{package}/index.json")
        response.raise_for_status()
        cp_info = response.json()

        self.version_dict = {Version(v): v for v in cp_info["versions"]}

    def update_version_windows(self, spec: Specifier) -> ConfigWinCP | None:
        # Specifier.filter selects all non pre-releases that match the spec,
        # unless there are only pre-releases, then it selects pre-releases
        # instead (like pip)
        unsorted_versions = spec.filter(self.version_dict)
        versions = sorted(unsorted_versions, reverse=True)

        log.debug("Windows %s %s has %s", self.arch, spec, ", ".join(str(v) for v in versions))

        if not versions:
            return None

        flags = "t" if self.free_threaded else ""
        version = versions[0]
        identifier = f"cp{version.major}{version.minor}{flags}-{self.arch}"
        return ConfigWinCP(
            identifier=identifier,
            version=self.version_dict[version],
            arch=self.arch_str,
        )


class PyPyVersions:
    def __init__(self, arch_str: ArchStr):
        response = requests.get("https://downloads.python.org/pypy/versions.json")
        response.raise_for_status()

        releases = [r for r in response.json() if r["pypy_version"] != "nightly"]
        for release in releases:
            release["pypy_version"] = Version(release["pypy_version"])
            release["python_version"] = Version(release["python_version"])

        self.releases = [
            r
            for r in releases
            if not r["pypy_version"].is_prerelease and not r["pypy_version"].is_devrelease
        ]
        self.arch = arch_str

    def get_arch_file(self, release: Mapping[str, Any]) -> str:
        urls: list[str] = [
            rf["download_url"]
            for rf in release["files"]
            if "" in rf["platform"] == f"win{self.arch}"
        ]
        return urls[0] if urls else ""

    def update_version_windows(self, spec: Specifier) -> ConfigWinCP:
        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])
        releases = [r for r in releases if self.get_arch_file(r)]

        if not releases:
            msg = f"PyPy Win {self.arch} not found for {spec}! {self.releases}"
            raise RuntimeError(msg)

        version_arch = "win32" if self.arch == "32" else "win_amd64"

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-{version_arch}"
        url = self.get_arch_file(release)

        return ConfigWinPP(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            arch=self.arch,
            url=url,
        )

    def update_version_macos(self, spec: Specifier) -> ConfigMacOS:
        if self.arch not in {"64", "ARM64"}:
            msg = f"'{self.arch}' arch not supported yet on macOS"
            raise RuntimeError(msg)

        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])

        if not releases:
            msg = f"PyPy macOS {self.arch} not found for {spec}!"
            raise RuntimeError(msg)

        release = releases[-1]
        version = release["python_version"]
        arch = "x86_64" if self.arch == "64" else self.arch.lower()
        identifier = f"pp{version.major}{version.minor}-macosx_{arch}"

        arch = "x64" if self.arch == "64" else self.arch.lower()
        (url,) = (
            rf["download_url"]
            for rf in release["files"]
            if "" in rf["platform"] == "darwin" and rf["arch"] == arch
        )

        return ConfigMacOS(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            url=url,
        )


class CPythonVersions:
    def __init__(self) -> None:
        response = requests.get(
            "https://www.python.org/api/v2/downloads/release/?is_published=true"
        )
        response.raise_for_status()

        releases_info = response.json()

        self.versions_dict: dict[Version, int] = {}
        for release in releases_info:
            # Removing the prefix, Python 3.9 would use: release["name"].removeprefix("Python ")
            version = Version(release["name"][7:])

            uri = int(release["resource_uri"].rstrip("/").split("/")[-1])
            self.versions_dict[version] = uri

    def update_version_macos(
        self, identifier: str, version: Version, spec: Specifier
    ) -> ConfigMacOS | None:
        # see note above on Specifier.filter
        unsorted_versions = spec.filter(self.versions_dict)
        sorted_versions = sorted(unsorted_versions, reverse=True)

        macver = "x10.9" if version <= Version("3.8.9999") else "11"
        file_ident = f"macos{macver}.pkg"

        for new_version in sorted_versions:
            # Find the first patch version that contains the requested file
            uri = self.versions_dict[new_version]
            response = requests.get(
                f"https://www.python.org/api/v2/downloads/release_file/?release={uri}"
            )
            response.raise_for_status()
            file_info = response.json()

            urls = [rf["url"] for rf in file_info if file_ident in rf["url"]]
            if urls:
                return ConfigMacOS(
                    identifier=identifier,
                    version=f"{new_version.major}.{new_version.minor}",
                    url=urls[0],
                )

        return None


# This is a universal interface to all the above Versions classes. Given an
# identifier, it updates a config dict.


class AllVersions:
    def __init__(self) -> None:
        self.windows_32 = WindowsVersions("32", False)
        self.windows_t_32 = WindowsVersions("32", True)
        self.windows_64 = WindowsVersions("64", False)
        self.windows_t_64 = WindowsVersions("64", True)
        self.windows_arm64 = WindowsVersions("ARM64", False)
        self.windows_t_arm64 = WindowsVersions("ARM64", True)
        self.windows_pypy_64 = PyPyVersions("64")

        self.macos_cpython = CPythonVersions()
        self.macos_pypy = PyPyVersions("64")
        self.macos_pypy_arm64 = PyPyVersions("ARM64")

    def update_config(self, config: MutableMapping[str, str]) -> None:
        identifier = config["identifier"]
        version = Version(config["version"])
        spec = Specifier(f"=={version.major}.{version.minor}.*")
        log.info("Reading in %r -> %s @ %s", str(identifier), spec, version)
        orig_config = copy.copy(config)
        config_update: AnyConfig | None = None

        # We need to use ** in update due to MyPy (probably a bug)
        if "macosx" in identifier:
            if identifier.startswith("cp"):
                config_update = self.macos_cpython.update_version_macos(identifier, version, spec)
            elif identifier.startswith("pp"):
                if "macosx_x86_64" in identifier:
                    config_update = self.macos_pypy.update_version_macos(spec)
                elif "macosx_arm64" in identifier:
                    config_update = self.macos_pypy_arm64.update_version_macos(spec)
        elif "t-win32" in identifier and identifier.startswith("cp"):
            config_update = self.windows_t_32.update_version_windows(spec)
        elif "win32" in identifier and identifier.startswith("cp"):
            config_update = self.windows_32.update_version_windows(spec)
        elif "t-win_amd64" in identifier and identifier.startswith("cp"):
            config_update = self.windows_t_64.update_version_windows(spec)
        elif "win_amd64" in identifier:
            if identifier.startswith("cp"):
                config_update = self.windows_64.update_version_windows(spec)
            elif identifier.startswith("pp"):
                config_update = self.windows_pypy_64.update_version_windows(spec)
        elif "t-win_arm64" in identifier and identifier.startswith("cp"):
            config_update = self.windows_t_arm64.update_version_windows(spec)
        elif "win_arm64" in identifier and identifier.startswith("cp"):
            config_update = self.windows_arm64.update_version_windows(spec)

        assert config_update is not None, f"{identifier} not found!"
        config.update(**config_update)

        if config != orig_config:
            log.info("  Updated %s to %s", orig_config, config)


@click.command()
@click.option("--force", is_flag=True)
@click.option(
    "--level", default="INFO", type=click.Choice(["WARNING", "INFO", "DEBUG"], case_sensitive=False)
)
def update_pythons(force: bool, level: str) -> None:
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    log.setLevel(level)

    all_versions = AllVersions()
    toml_file_path = RESOURCES_DIR / "build-platforms.toml"

    original_toml = toml_file_path.read_text()
    with toml_file_path.open("rb") as f:
        configs = tomllib.load(f)

    for config in configs["windows"]["python_configurations"]:
        all_versions.update_config(config)

    for config in configs["macos"]["python_configurations"]:
        all_versions.update_config(config)

    result_toml = dump_python_configurations(configs)

    rich.print()  # spacer

    if original_toml == result_toml:
        rich.print("[green]Check complete, Python configurations unchanged.")
        return

    rich.print("Python configurations updated.")
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
    update_pythons()
