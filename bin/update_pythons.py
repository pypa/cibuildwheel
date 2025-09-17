#!/usr/bin/env python3


import difflib
import logging
import operator
import re
import tomllib
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, Final, Literal, TypedDict
from xml.etree import ElementTree as ET

import click
import requests
import rich
from packaging.specifiers import Specifier
from packaging.version import Version
from rich.logging import RichHandler
from rich.syntax import Syntax

from cibuildwheel.extra import dump_python_configurations, get_pyodide_xbuildenv_info
from cibuildwheel.platforms.android import android_triplet

log = logging.getLogger("cibw")

# Looking up the dir instead of using utils.resources_dir
# since we want to write to it.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
RESOURCES_DIR: Final[Path] = DIR / "cibuildwheel/resources"


ArchStr = Literal["32", "64", "ARM64"]


class Config(TypedDict):
    identifier: str
    version: str


class ConfigUrl(Config):
    url: str


class ConfigPyodide(Config):
    default_pyodide_version: str
    node_version: str


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

    def update_version_windows(self, spec: Specifier) -> Config | None:
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
        return Config(
            identifier=identifier,
            version=self.version_dict[version],
        )


class GraalPyVersions:
    def __init__(self) -> None:
        response = requests.get("https://api.github.com/repos/oracle/graalpython/releases")
        response.raise_for_status()

        releases = response.json()
        gp_version_re = re.compile(r"-(\d+\.\d+\.\d+)$")
        cp_version_re = re.compile(r"Python (\d+\.\d+(?:\.\d+)?)")
        for release in releases:
            m = gp_version_re.search(release["tag_name"])
            if m:
                release["graalpy_version"] = Version(m.group(1))
            m = cp_version_re.search(release["body"])
            if m:
                release["python_version"] = Version(m.group(1))

        self.releases = [r for r in releases if "graalpy_version" in r and "python_version" in r]

    def update_version(self, identifier: str, spec: Specifier) -> ConfigUrl:
        if "x86_64" in identifier or "amd64" in identifier:
            arch = "x86_64"
        elif "arm64" in identifier or "aarch64" in identifier:
            arch = "aarch64"
        else:
            msg = f"{identifier} not supported yet on GraalPy"
            raise RuntimeError(msg)

        gpspec_str = identifier.split("-")[0].split("_")[1]
        if "." not in gpspec_str and len(gpspec_str) == 3:
            gpspec_str = gpspec_str[:2] + "." + gpspec_str[-1]
        gpspec = Specifier(f"=={gpspec_str}.*")

        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = [r for r in self.releases if gpspec.contains(r["graalpy_version"])]
        releases = sorted(releases, key=lambda r: r["graalpy_version"])

        if not releases:
            msg = f"GraalPy {arch} not found for {spec}!"
            raise RuntimeError(msg)

        release = releases[-1]
        version = release["python_version"]
        gpversion = release["graalpy_version"]

        if "macosx" in identifier:
            arch = "x86_64" if "x86_64" in identifier else "arm64"
            platform = "macos"
        elif "win" in identifier:
            arch = "aarch64" if "arm64" in identifier else "x86_64"
            platform = "windows"
        else:
            msg = "GraalPy provides downloads for macOS and Windows and is included for manylinux"
            raise RuntimeError(msg)

        arch = "amd64" if arch == "x86_64" else "aarch64"
        ext = "zip" if "win" in identifier else "tar.gz"
        (url,) = (
            rf["browser_download_url"]
            for rf in release["assets"]
            if rf["name"].endswith(f"{platform}-{arch}.{ext}")
            and rf["name"].startswith(f"graalpy-{gpversion.major}")
        )

        return ConfigUrl(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            url=url,
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

    def update_version_windows(self, spec: Specifier) -> ConfigUrl:
        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=operator.itemgetter("pypy_version"))
        releases = [r for r in releases if self.get_arch_file(r)]

        if not releases:
            msg = f"PyPy Win {self.arch} not found for {spec}! {self.releases}"
            raise RuntimeError(msg)

        version_arch = "win32" if self.arch == "32" else "win_amd64"

        release = releases[-1]
        version = release["python_version"]
        identifier = f"pp{version.major}{version.minor}-{version_arch}"
        url = self.get_arch_file(release)

        return ConfigUrl(
            identifier=identifier,
            version=f"{version.major}.{version.minor}",
            url=url,
        )

    def update_version_macos(self, spec: Specifier) -> ConfigUrl:
        if self.arch not in {"64", "ARM64"}:
            msg = f"'{self.arch}' arch not supported yet on macOS"
            raise RuntimeError(msg)

        releases = [r for r in self.releases if spec.contains(r["python_version"])]
        releases = sorted(releases, key=operator.itemgetter("pypy_version"))

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

        return ConfigUrl(
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
            # Skip the pymanager releases
            if not release["slug"].startswith("python"):
                continue

            # Removing the prefix
            version = Version(release["name"].removeprefix("Python "))

            uri = int(release["resource_uri"].rstrip("/").split("/")[-1])
            self.versions_dict[version] = uri

    def update_version(self, identifier: str, spec: Specifier, file_ident: str) -> ConfigUrl | None:
        # see note above on Specifier.filter
        unsorted_versions = spec.filter(self.versions_dict)
        sorted_versions = sorted(unsorted_versions, reverse=True)

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
                return ConfigUrl(
                    identifier=identifier,
                    version=f"{new_version.major}.{new_version.minor}",
                    url=urls[0],
                )

        return None

    def update_version_macos(
        self, identifier: str, version: Version, spec: Specifier
    ) -> ConfigUrl | None:
        macver = "x10.9" if version <= Version("3.8.9999") else "11"
        return self.update_version(identifier, spec, f"macos{macver}.pkg")

    def update_version_android(self, identifier: str, spec: Specifier) -> ConfigUrl | None:
        return self.update_version(identifier, spec, android_triplet(identifier))


class MavenVersions:
    MAVEN_URL = "https://repo.maven.apache.org/maven2/com/chaquo/python/python"

    def __init__(self) -> None:
        response = requests.get(f"{self.MAVEN_URL}/maven-metadata.xml")
        response.raise_for_status()
        root = ET.fromstring(response.text)

        self.versions: list[Version] = []
        for version_elem in root.findall("./versioning/versions/version"):
            version_str = version_elem.text
            assert isinstance(version_str, str), version_str
            self.versions.append(Version(version_str))

    def update_version_android(self, identifier: str, spec: Specifier) -> ConfigUrl | None:
        sorted_versions = sorted(spec.filter(self.versions), reverse=True)

        # Return a config using the highest version for the given specifier.
        if sorted_versions:
            max_version = sorted_versions[0]
            triplet = android_triplet(identifier)
            return ConfigUrl(
                identifier=identifier,
                version=f"{max_version.major}.{max_version.minor}",
                url=f"{self.MAVEN_URL}/{max_version}/python-{max_version}-{triplet}.tar.gz",
            )
        else:
            return None


class CPythonIOSVersions:
    def __init__(self) -> None:
        response = requests.get(
            "https://api.github.com/repos/beeware/Python-Apple-support/releases",
            headers={
                "Accept": "application/vnd.github+json",
                "X-Github-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()

        releases_info = response.json()
        self.versions_dict: dict[Version, dict[int, str]] = {}

        # Each release has a name like "3.13-b4"
        for release in releases_info:
            py_version, build = release["name"].split("-")
            version = Version(py_version)
            self.versions_dict.setdefault(version, {})

            # There are several release assets associated with each release;
            # The name of the asset will be something like
            # "Python-3.11-iOS-support.b4.tar.gz". Store all builds that are
            # "-iOS-support" builds, retaining the download URL.
            for asset in release["assets"]:
                filename, build, _, _ = asset["name"].rsplit(".", 3)
                if filename.endswith("-iOS-support"):
                    self.versions_dict[version][int(build[1:])] = asset["browser_download_url"]

    def update_version_ios(self, identifier: str, version: Version) -> ConfigUrl | None:
        # Return a config using the highest build number for the given version.
        urls = [url for _, url in sorted(self.versions_dict.get(version, {}).items())]
        if urls:
            return ConfigUrl(
                identifier=identifier,
                version=str(version),
                url=urls[-1],
            )

        return None


class PyodideVersions:
    def __init__(self) -> None:
        xbuildenv_info = get_pyodide_xbuildenv_info()
        self.releases = xbuildenv_info["releases"]

    def update_version_pyodide(
        self, identifier: str, version: Version, spec: Specifier, node_version: str
    ) -> ConfigPyodide | None:
        # get releases that match the python version
        releases = [
            r for r in self.releases.values() if spec.contains(Version(r["python_version"]))
        ]
        # sort by version, latest first
        releases.sort(key=lambda r: Version(r["version"]), reverse=True)

        if not releases:
            msg = f"Pyodide not found for {spec}!"
            raise ValueError(msg)

        final_releases = [r for r in releases if not Version(r["version"]).is_prerelease]

        # prefer a final release if available, otherwise use the latest
        # pre-release
        release = final_releases[0] if final_releases else releases[0]

        return ConfigPyodide(
            identifier=identifier,
            version=str(version),
            default_pyodide_version=release["version"],
            node_version=node_version,
        )


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

        self.cpython = CPythonVersions()
        self.macos_pypy = PyPyVersions("64")
        self.macos_pypy_arm64 = PyPyVersions("ARM64")

        self.maven = MavenVersions()
        self.ios_cpython = CPythonIOSVersions()

        self.graalpy = GraalPyVersions()

        self.pyodide = PyodideVersions()

    def update_config(self, config: MutableMapping[str, str]) -> None:
        identifier = config["identifier"]
        version = Version(config["version"])
        spec = Specifier(f"=={version.major}.{version.minor}.*")
        log.info("Reading in %r -> %s @ %s", str(identifier), spec, version)
        config_update: Config | None = None

        # We need to use ** in update due to MyPy (probably a bug)
        if "macosx" in identifier:
            if identifier.startswith("cp"):
                config_update = self.cpython.update_version_macos(identifier, version, spec)
            elif identifier.startswith("pp"):
                if "macosx_x86_64" in identifier:
                    config_update = self.macos_pypy.update_version_macos(spec)
                elif "macosx_arm64" in identifier:
                    config_update = self.macos_pypy_arm64.update_version_macos(spec)
            elif identifier.startswith("gp"):
                config_update = self.graalpy.update_version(identifier, spec)
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
            elif identifier.startswith("gp"):
                config_update = self.graalpy.update_version(identifier, spec)
        elif "t-win_arm64" in identifier and identifier.startswith("cp"):
            config_update = self.windows_t_arm64.update_version_windows(spec)
        elif "win_arm64" in identifier and identifier.startswith("cp"):
            config_update = self.windows_arm64.update_version_windows(spec)
        elif "android" in identifier:
            # Python 3.13 is released by Chaquopy on Maven Central.
            # Python 3.14 and newer have official releases on python.org.
            versions = self.maven if identifier.startswith("cp313") else self.cpython
            config_update = versions.update_version_android(identifier, spec)
        elif "ios" in identifier:
            config_update = self.ios_cpython.update_version_ios(identifier, version)
        elif "pyodide" in identifier:
            config_update = self.pyodide.update_version_pyodide(
                identifier, version, spec, config["node_version"]
            )

        assert config_update is not None, f"{identifier} not found!"
        if config_update != config:
            log.info("  Updated %s to %s", config, config_update)
            config.clear()
            config.update(**config_update)


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

    for platform in ["windows", "macos", "android", "ios", "pyodide"]:
        for config in configs[platform]["python_configurations"]:
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
