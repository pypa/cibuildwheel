#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "packaging",
#   "requests",
# ]
# ///

import configparser
import dataclasses
from functools import cache
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


IMAGES = [
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
        "manylinux_2_28",
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
    # manylinux_2_31 images
    PyPAImage("manylinux_2_31", ["armv7l"]),
    # manylinux_2_34 images
    PyPAImage(
        "manylinux_2_34",
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
    # manylinux_2_35 images
    PyPAImage("manylinux_2_35", ["armv7l"]),
    # manylinux_2_39 images
    PyPAImage("manylinux_2_39", ["riscv64"]),
    # musllinux_1_2 images
    PyPAImage(
        "musllinux_1_2", ["x86_64", "i686", "aarch64", "ppc64le", "s390x", "armv7l", "riscv64"]
    ),
]


@cache
def quay_lookup(image_name: str, tag_name: str) -> tuple[str, str]:
    _, _, repository_name = image_name.partition("/")
    if tag_name == "latest":
        url = f"https://quay.io/api/v1/repository/{repository_name}?includeTags=true"
    else:
        url = f"https://quay.io/api/v1/repository/{repository_name}/tag?specificTag={tag_name}"
    response = requests.get(url)
    response.raise_for_status()
    info = response.json()
    if tag_name == "latest":
        tags_dict = info["tags"]
        tag_info = tags_dict.pop(tag_name)
        # find the tag whose manifest matches 'latest'
        tag_name, digest = next(
            (name, info["manifest_digest"])
            for (name, info) in tags_dict.items()
            if info["manifest_digest"] == tag_info["manifest_digest"]
        )
    else:
        tags_list = info["tags"]
        tag_info = next(tag for tag in tags_list if tag["name"] == tag_name)
        digest = tag_info["manifest_digest"]

    return tag_name, digest


@cache
def ghcr_lookup(image_name: str, tag_name: str) -> tuple[str, str]:
    repository = image_name[8:]
    response = requests.get(
        "https://ghcr.io/token", params={"scope": f"repository:{repository}:pull"}
    )
    response.raise_for_status()
    token = response.json()["token"]
    if tag_name == "latest":
        response = requests.get(
            f"https://ghcr.io/v2/{repository}/tags/list",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        info = response.json()
        ghcr_tags = [(Version(tag), tag) for tag in info["tags"] if tag != "latest"]
        ghcr_tags.sort(reverse=True)
        tag_name = ghcr_tags[0][1]

    response = requests.head(
        f"https://ghcr.io/v2/{repository}/manifests/{tag_name}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, application/vnd.oci.artifact.manifest.v1+json",
        },
    )
    response.raise_for_status()
    digest = response.headers["Docker-Content-Digest"]
    return tag_name, digest


@cache
def dockerhub_lookup(image_name: str, tag_name: str) -> tuple[str, str]:
    response = requests.get(f"https://hub.docker.com/v2/repositories/{image_name}/tags")
    response.raise_for_status()
    tags = response.json()["results"]
    if tag_name == "latest":
        latest_tag = next(tag for tag in tags if tag["name"] == "latest")
        # i don't know what it would mean to have multiple images per tag
        assert len(latest_tag["images"]) == 1
        digest = latest_tag["images"][0]["digest"]

        pinned_tag = next(
            tag for tag in tags if tag != latest_tag and tag["images"][0]["digest"] == digest
        )
    else:
        pinned_tag = next(tag for tag in tags if tag["name"] == tag_name)
        digest = pinned_tag["images"][0]["digest"]
    tag_name = pinned_tag["name"]
    return tag_name, digest


def main() -> None:
    config = configparser.ConfigParser()
    for image in IMAGES:
        # get the tag name whose digest matches 'latest'
        # if image has been pinned, do not update
        search_tag = image.tag or "latest"
        if image.image_name.startswith("quay.io/"):
            lookup = quay_lookup
        elif image.image_name.startswith("ghcr.io/"):
            lookup = ghcr_lookup
        else:
            lookup = dockerhub_lookup

        tag_name, digest = lookup(image.image_name, search_tag)
        for platform in image.platforms:
            if not config.has_section(platform):
                config[platform] = {}
            image_name = image.image_name
            if image.use_platform_suffix:
                image_name = f"{image_name}_{platform.removeprefix('pypy_')}"
                _, digest = lookup(image_name, tag_name)
            assert digest.startswith("sha256:")
            config[platform][image.manylinux_version] = f"{image_name}@{digest}  # {tag_name}"

    with open(RESOURCES / "pinned_docker_images.cfg", "w") as f:
        config.write(f)


if __name__ == "__main__":
    main()
