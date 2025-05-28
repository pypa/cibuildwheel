#!/usr/bin/env python3

import configparser
import dataclasses
from pathlib import Path

import requests
from packaging.version import Version

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "cibuildwheel/resources"


@dataclasses.dataclass(frozen=True)
class Image:
    manylinux_version: str
    platforms: list[str]
    image_name: str
    tag: str | None = None  # Set this to pin the image
    use_platform_suffix: bool = False


class PyPAImage(Image):
    def __init__(self, manylinux_version: str, platforms: list[str], tag: str | None = None):
        image_name = f"quay.io/pypa/{manylinux_version}"
        super().__init__(manylinux_version, platforms, image_name, tag, True)


images = [
    # manylinux2014 images
    PyPAImage(
        "manylinux2014",
        [
            "x86_64",
            "i686",
            "aarch64",
            "ppc64le",
            "s390x",
            "pypy_x86_64",
            "pypy_i686",
            "pypy_aarch64",
        ],
    ),
    # manylinux_2_28 images
    PyPAImage(
        "manylinux_2_28", ["x86_64", "aarch64", "ppc64le", "s390x", "pypy_x86_64", "pypy_aarch64"]
    ),
    # manylinux_2_31 images
    PyPAImage("manylinux_2_31", ["armv7l"]),
    # manylinux_2_34 images
    PyPAImage(
        "manylinux_2_34", ["x86_64", "aarch64", "ppc64le", "s390x", "pypy_x86_64", "pypy_aarch64"]
    ),
    # musllinux_1_2 images
    PyPAImage("musllinux_1_2", ["x86_64", "i686", "aarch64", "ppc64le", "s390x", "armv7l"]),
]

config = configparser.ConfigParser()

for image in images:
    # get the tag name whose digest matches 'latest'
    if image.tag is not None:
        # image has been pinned, do not update
        tag_name = image.tag
    elif image.image_name.startswith("quay.io/"):
        _, _, repository_name = image.image_name.partition("/")
        response = requests.get(
            f"https://quay.io/api/v1/repository/{repository_name}?includeTags=true"
        )
        response.raise_for_status()
        repo_info = response.json()
        tags_dict = repo_info["tags"]

        latest_tag = tags_dict.pop("latest")
        # find the tag whose manifest matches 'latest'
        tag_name = next(
            name
            for (name, info) in tags_dict.items()
            if info["manifest_digest"] == latest_tag["manifest_digest"]
        )
    elif image.image_name.startswith("ghcr.io/"):
        repository = image.image_name[8:]
        response = requests.get(
            "https://ghcr.io/token", params={"scope": f"repository:{repository}:pull"}
        )
        response.raise_for_status()
        token = response.json()["token"]
        response = requests.get(
            f"https://ghcr.io/v2/{repository}/tags/list",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        ghcr_tags = [(Version(tag), tag) for tag in response.json()["tags"] if tag != "latest"]
        ghcr_tags.sort(reverse=True)
        tag_name = ghcr_tags[0][1]
    else:
        response = requests.get(f"https://hub.docker.com/v2/repositories/{image.image_name}/tags")
        response.raise_for_status()
        tags = response.json()["results"]

        latest_tag = next(tag for tag in tags if tag["name"] == "latest")
        # i don't know what it would mean to have multiple images per tag
        assert len(latest_tag["images"]) == 1
        digest = latest_tag["images"][0]["digest"]

        pinned_tag = next(
            tag for tag in tags if tag != latest_tag and tag["images"][0]["digest"] == digest
        )
        tag_name = pinned_tag["name"]

    for platform in image.platforms:
        if not config.has_section(platform):
            config[platform] = {}
        suffix = ""
        if image.use_platform_suffix:
            suffix = f"_{platform.removeprefix('pypy_')}"
        config[platform][image.manylinux_version] = f"{image.image_name}{suffix}:{tag_name}"

if not config.has_section("riscv64"):
    config["riscv64"] = {}

with open(RESOURCES / "pinned_docker_images.cfg", "w") as f:
    config.write(f)
