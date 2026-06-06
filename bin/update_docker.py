#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "packaging",
#   "requests",
# ]
# ///

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


class CudaImage(Image):
    """
    A CUDA manylinux image from the manylinux_cuda project.

    Each architecture has its own repository and the images are only published
    with a ``latest`` tag, so (unlike the PyPA images) these are pinned by
    digest. ``{arch}`` in the image name is substituted per platform.
    """

    def __init__(self, manylinux_version: str, cuda_version: str, platforms: list[str]):
        alias = f"{manylinux_version}_cuda{cuda_version}"
        image_name = f"quay.io/manylinux_cuda/{manylinux_version}_{{arch}}_cuda{cuda_version}"
        super().__init__(alias, platforms, image_name)


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
    # CUDA manylinux images (x86_64 and aarch64 only, pinned by digest)
    *(
        CudaImage(manylinux_version, cuda_version, ["x86_64", "aarch64"])
        for manylinux_version in ("manylinux_2_28", "manylinux_2_34")
        for cuda_version in ("12_9", "13_1")
    ),
]

config = configparser.ConfigParser()

for image in images:
    if "{arch}" in image.image_name:
        # Per-architecture repositories pinned by digest (the 'latest' tag is
        # the only published tag, so there is no dated tag to pin to).
        for platform in image.platforms:
            arch = platform.removeprefix("pypy_")
            image_name = image.image_name.format(arch=arch)
            _, _, repository_name = image_name.partition("/")
            response = requests.get(
                f"https://quay.io/api/v1/repository/{repository_name}?includeTags=true"
            )
            response.raise_for_status()
            digest = response.json()["tags"]["latest"]["manifest_digest"]
            if not config.has_section(platform):
                config[platform] = {}
            config[platform][image.manylinux_version] = f"{image_name}@{digest}"
        continue

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

with open(RESOURCES / "pinned_docker_images.cfg", "w") as f:
    config.write(f)
