#!/usr/bin/env python3

import copy
import difflib
import logging
from pathlib import Path
from typing import Dict, Optional, Union

import click
import requests
import rich
import toml
from packaging.specifiers import Specifier
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel.extra import InlineArrayDictEncoder
from cibuildwheel.typing import Final, Literal, TypedDict

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"


ArchStr = Literal["32", "64"]


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
    def __init__(self, arch_str: ArchStr) -> None:

        response = requests.get("https://api.nuget.org/v3/index.json")
        response.raise_for_status()
        api_info = response.json()

        for resource in api_info["resources"]:
            if resource["@type"] == "PackageBaseAddress/3.0.0":
                endpoint = resource["@id"]

        ARCH_DICT = {"32": "win32", "64": "win_amd64"}
        PACKAGE_DICT = {"32": "pythonx86", "64": "python"}

        self.arch_str = arch_str
        self.arch = ARCH_DICT[arch_str]
        package = PACKAGE_DICT[arch_str]

        response = requests.get(f"{endpoint}{package}/index.json")
        response.raise_for_status()
        cp_info = response.json()

        versions = (Version(v) for v in cp_info["versions"])
        self.versions = sorted(v for v in versions if not v.is_devrelease)

    def update_version_windows(self, spec: Specifier) -> Optional[ConfigWinCP]:
        versions = sorted(v for v in self.versions if spec.contains(v))
        if not all(v.is_prerelease for v in versions):
            versions = [v for v in versions if not v.is_prerelease]
        log.debug(f"Windows {self.arch} {spec} has {', '.join(str(v) for v in versions)}")

        if not versions:
            return None

        version = versions[-1]
        identifier = f"cp{version.major}{version.minor}-{self.arch}"
        result = ConfigWinCP(
            identifier=identifier,
            version=str(version),
            arch=self.arch_str,
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

        self.releases = [
            r for r in releases if not r["pypy_version"].is_prerelease and not r["pypy_version"].is_devrelease
        ]
        self.arch = arch_str

    def update_version_windows(self, spec: Specifier) -> ConfigWinCP:
        if self.arch != "32":
            raise RuntimeError("64 bit releases not supported yet on Windows")

        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])

        if not releases:
            raise RuntimeError(f"PyPy Win {self.arch} not found for {spec}! {self.releases}")

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-win32"

        (url,) = [rf["download_url"] for rf in release["files"] if "" in rf["platform"] == "win32"]

        return ConfigWinPP(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            arch="32",
            url=url,
        )

    def update_version_macos(self, spec: Specifier) -> ConfigMacOS:
        if self.arch != "64":
            raise RuntimeError("Other archs not supported yet on macOS")

        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=lambda r: r["pypy_version"])

        if not releases:
            raise RuntimeError(f"PyPy macOS {self.arch} not found for {spec}!")

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-macosx_x86_64"

        (url,) = [
            rf["download_url"] for rf in release["files"] if "" in rf["platform"] == "darwin" and rf["arch"] == "x64"
        ]

        return ConfigMacOS(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            url=url,
        )


class CPythonVersions:
    def __init__(self) -> None:

        response = requests.get("https://www.python.org/api/v2/downloads/release/?is_published=true")
        response.raise_for_status()

        releases_info = response.json()

        self.versions_dict: Dict[Version, int] = {}
        for release in releases_info:
            # Removing the prefix, Python 3.9 would use: release["name"].removeprefix("Python ")
            version = Version(release["name"][7:])

            if not version.is_prerelease and not version.is_devrelease:
                uri = int(release["resource_uri"].rstrip("/").split("/")[-1])
                self.versions_dict[version] = uri

    def update_version_macos(self, identifier: str, spec: Specifier) -> Optional[ConfigMacOS]:
        file_idents = ("macos11.0.pkg", "macosx10.9.pkg", "macosx10.6.pkg")
        sorted_versions = sorted(v for v in self.versions_dict if spec.contains(v))

        for version in reversed(sorted_versions):
            # Find the first patch version that contains the requested file
            uri = self.versions_dict[version]
            response = requests.get(f"https://www.python.org/api/v2/downloads/release_file/?release={uri}")
            response.raise_for_status()
            file_info = response.json()

            for file_ident in file_idents:
                urls = [rf["url"] for rf in file_info if file_ident in rf["url"]]
                if urls:
                    return ConfigMacOS(
                        identifier=identifier,
                        version=f"{version.major}.{version.minor}",
                        url=urls[0],
                    )

        return None


# This is a universal interface to all the above Versions classes. Given an
# identifier, it updates a config dict.


class AllVersions:
    def __init__(self) -> None:
        self.windows_32 = WindowsVersions("32")
        self.windows_64 = WindowsVersions("64")
        self.windows_pypy = PyPyVersions("32")

        self.macos_cpython = CPythonVersions()
        self.macos_pypy = PyPyVersions("64")

    def update_config(self, config: Dict[str, str]) -> None:
        identifier = config["identifier"]
        version = Version(config["version"])
        spec = Specifier(f"=={version.major}.{version.minor}.*")
        log.info(f"Reading in '{identifier}' -> {spec} @ {version}")
        orig_config = copy.copy(config)
        config_update: Optional[AnyConfig]

        # We need to use ** in update due to MyPy (probably a bug)
        if "macos" in identifier:
            if identifier.startswith("pp"):
                config_update = self.macos_pypy.update_version_macos(spec)
            else:
                config_update = self.macos_cpython.update_version_macos(identifier, spec)

            assert config_update is not None, f"MacOS {spec} not found!"
            config.update(**config_update)
        elif "win32" in identifier:
            if identifier.startswith("pp"):
                config.update(**self.windows_pypy.update_version_windows(spec))
            else:
                config_update = self.windows_32.update_version_windows(spec)
                if config_update:
                    config.update(**config_update)
        elif "win_amd64" in identifier:
            config_update = self.windows_64.update_version_windows(spec)
            if config_update:
                config.update(**config_update)

        if config != orig_config:
            log.info(f"  Updated {orig_config} to {config}")


@click.command()
@click.option("--force", is_flag=True)
@click.option("--level", default="INFO", type=click.Choice(["INFO", "DEBUG", "TRACE"], case_sensitive=False))
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
    configs = toml.loads(original_toml)

    for config in configs["windows"]["python_configurations"]:
        all_versions.update_config(config)

    for config in configs["macos"]["python_configurations"]:
        all_versions.update_config(config)

    result_toml = toml.dumps(configs, encoder=InlineArrayDictEncoder())  # type: ignore

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
