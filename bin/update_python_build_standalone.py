#!/usr/bin/env python3

import json

from cibuildwheel.extra import github_api_request
from cibuildwheel.util.python_build_standalone import (
    PythonBuildStandaloneAsset,
    PythonBuildStandaloneReleaseData,
)
from cibuildwheel.util.resources import PYTHON_BUILD_STANDALONE_RELEASES


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

    assets: list[PythonBuildStandaloneAsset] = []

    for github_asset in github_assets:
        name = github_asset["name"]
        if not name.endswith("install_only.tar.gz"):
            continue
        url = github_asset["browser_download_url"]
        assets.append({"name": name, "url": url})

    # Write the assets to the JSON file. One day, we might need to support
    # multiple releases, but for now, we only support the latest one
    json_file_contents: PythonBuildStandaloneReleaseData = {
        "releases": [
            {
                "tag": latest_tag,
                "assets": assets,
            }
        ]
    }

    with PYTHON_BUILD_STANDALONE_RELEASES.open("w", encoding="utf-8") as f:
        json.dump(json_file_contents, f, indent=2)
        # Add a trailing newline, our pre-commit hook requires it
        f.write("\n")

    print(
        f"Updated {PYTHON_BUILD_STANDALONE_RELEASES.name} with {len(assets)} assets for tag {latest_tag}"
    )


if __name__ == "__main__":
    main()
