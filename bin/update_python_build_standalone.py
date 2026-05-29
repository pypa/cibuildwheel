#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "cibuildwheel",
#   "requests",
# ]
#
# [tool.uv.sources]
# cibuildwheel = { path = ".." }
# ///

import json
from pathlib import Path
from typing import Final

import requests

from cibuildwheel.extra import github_api_request
from cibuildwheel.util.python_build_standalone import (
    PythonBuildStandaloneAsset,
    PythonBuildStandaloneReleaseData,
)

# Resolve path relative to this script so writes go to the source checkout,
# not the uv-installed copy of the package.
DIR: Final[Path] = Path(__file__).parent.parent.resolve()
PYTHON_BUILD_STANDALONE_RELEASES: Final[Path] = (
    DIR / "cibuildwheel/resources/python-build-standalone-releases.json"
)


def main() -> None:
    """
    This script updates the vendored list of release assets to the latest
    version of astral-sh/python-build-standalone.
    """

    # Get the latest release tag from the GitHub API
    latest_release = github_api_request("repos/astral-sh/python-build-standalone/releases/latest")
    latest_tag = latest_release["tag_name"]

    # Get the list of assets for the latest release
    github_assets = github_api_request(
        f"repos/astral-sh/python-build-standalone/releases/tags/{latest_tag}"
    )["assets"]

    # Build a sha256 map from the SHA256SUMS file in the release
    sha256_sums_urls = [
        ga["browser_download_url"] for ga in github_assets if ga["name"] == "SHA256SUMS"
    ]
    name_to_sha256: dict[str, str] = {}
    if sha256_sums_urls:
        response = requests.get(sha256_sums_urls[0])
        response.raise_for_status()
        for line in response.text.splitlines():
            parts = line.split()
            if len(parts) == 2:
                sha256_hex, filename = parts
                # The filename may have a leading "./" or spaces - strip it
                name_to_sha256[filename.lstrip("./")] = sha256_hex

    assets = [
        PythonBuildStandaloneAsset(
            name=ga["name"],
            url=ga["browser_download_url"],
            sha256=name_to_sha256.get(ga["name"], ""),
        )
        for ga in github_assets
        if ga["name"].endswith("install_only.tar.gz")
    ]

    # Try to keep output order stable
    assets = sorted(assets, key=lambda x: x["name"])

    # Write the assets to the JSON file. One day, we might need to support
    # multiple releases, but for now, we only support the latest one
    json_file_contents = PythonBuildStandaloneReleaseData(
        releases=[
            {
                "tag": latest_tag,
                "assets": assets,
            }
        ]
    )

    with PYTHON_BUILD_STANDALONE_RELEASES.open("w", encoding="utf-8") as f:
        json.dump(json_file_contents, f, indent=2)
        # Add a trailing newline, our pre-commit hook requires it
        f.write("\n")

    print(
        f"Updated {PYTHON_BUILD_STANDALONE_RELEASES.name} with {len(assets)} assets for tag {latest_tag}"
    )


if __name__ == "__main__":
    main()
