#!/usr/bin/env python3

import sys
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import toml
from packaging.version import Version

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

# Use pretty printing for debugging
# from rich import print


allow_prerelease = False


class InlineArrayDictEncoder(toml.encoder.TomlEncoder):
    def dump_sections(self, o: dict, sup: str):
        if all(isinstance(a, list) for a in o.values()):
            val = ""
            for k, v in o.items():
                inner = ",\n  ".join(self.dump_inline_table(d_i).strip() for d_i in v)
                val += f"{k} = [\n  {inner},\n]\n"
            return val, self._dict()
        else:
            return super().dump_sections(o, sup)


DIR = Path(__file__).parent.parent.resolve()
RESOURCES_DIR = DIR / "cibuildwheel/resources"


class ConfigWinCP(TypedDict):
    identifier: str
    version: str
    arch: str


class ConfigWinPP(TypedDict):
    identifier: str
    version: str
    arch: str
    url: str


def get_cpython_windows() -> Dict[str, List[Version]]:
    response = requests.get("https://api.nuget.org/v3/index.json")
    response.raise_for_status()
    api_info = response.json()

    for resource in api_info["resources"]:
        if resource["@type"] == "PackageBaseAddress/3.0.0":
            endpoint = resource["@id"]

    cp_versions: Dict[str, List[Version]] = {"64": [], "32": []}
    for id, package in [("64", "python"), ("32", "pythonx86")]:
        response = requests.get(f"{endpoint}{package}/index.json")
        response.raise_for_status()
        cp_info = response.json()

        for version_str in cp_info["versions"]:
            version = Version(version_str)
            if version.is_devrelease:
                continue
            if not allow_prerelease and version.is_prerelease:
                continue
            cp_versions[id].append(version)
        cp_versions[id].sort()

    return cp_versions


def get_pypy_windows(
    plat_arch: str = "win32-x86",
) -> Dict[str, List[Tuple[Version, str]]]:

    response = requests.get("https://downloads.python.org/pypy/versions.json")
    response.raise_for_status()
    pp_realeases = response.json()
    pp_versions = defaultdict(list)

    for pp_realease in pp_realeases:
        if pp_realease["pypy_version"] == "nightly":
            continue
        version = Version(pp_realease["pypy_version"])
        python_version = Version(pp_realease["python_version"])
        python_version_str = f"{python_version.major}.{python_version.minor}"
        url = None
        for file in pp_realease["files"]:
            if f"{file['platform']}-{file['arch']}" == plat_arch:
                url = file["download_url"]
                break
        if url:
            pp_versions[python_version_str].append((version, url))

    return pp_versions


# Debugging printout:
# print(get_cpython_windows())
# print()
# print("[bold]Getting PyPy")
# print(get_pypy_windows())

ARCH_DICT = {"32": "win32", "64": "win_amd64"}


def build_ids_cp(in_dict: Dict[str, List[Version]]) -> List[ConfigWinCP]:
    items: List[ConfigWinCP] = []
    for arch in in_dict:
        for minor, grp in groupby(in_dict[arch], lambda v: v.minor):
            # Filter pre-releases, unless it's all pre-releases
            if not all(v.is_devrelease for v in grp):
                grp = filter(lambda v: not v.is_devrelease, grp)

            version = sorted(grp)[-1]
            identifier = f"cp3{minor}-{ARCH_DICT[arch]}"

            items.append(
                ConfigWinCP(
                    identifier=identifier,
                    version=str(version),
                    arch=arch,
                )
            )

    return items


def build_ids_pp(in_dict: Dict[str, List[Tuple[Version, str]]]) -> List[ConfigWinPP]:
    items: List[ConfigWinPP] = []
    for vers, matches in in_dict.items():
        vers_id = vers.replace(".", "")
        if not all(v[0].is_devrelease for v in matches):
            matches = list(filter(lambda v: not v[0].is_devrelease, matches))

        version, url = sorted(matches, key=lambda v: v[0])[-1]
        identifier = f"pp{vers_id}-win32"

        items.append(
            ConfigWinPP(
                identifier=identifier,
                version=vers,
                arch="32",
                url=url,
            )
        )

    return items


windows_configs = [
    *build_ids_cp(get_cpython_windows()),
    *build_ids_pp(get_pypy_windows()),
]

configs = toml.load(RESOURCES_DIR / "build-platforms.toml")
origpy2 = list(
    filter(
        lambda c: c["identifier"].startswith("cp27"),
        configs["windows"]["python_configurations"],
    )
)

items = origpy2 + windows_configs
new_configs = sorted(items, key=lambda x: (x["identifier"][:3], x["identifier"][3:]))

configs["windows"]["python_configurations"] = new_configs

with open(RESOURCES_DIR / "build-platforms.toml", "w") as f:
    toml.dump(configs, f, encoder=InlineArrayDictEncoder())  # type: ignore
