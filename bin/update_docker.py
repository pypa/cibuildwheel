#!/usr/bin/env python3
from __future__ import annotations

import configparser
from pathlib import Path
from typing import NamedTuple

import requests

DIR = Path(__file__).parent.resolve()
RESOURCES = DIR.parent / "cibuildwheel/resources"


class Image(NamedTuple):
    manylinux_version: str
    platform: str
    image_name: str
    tag: str | None  # Set this to pin the image


images = [
    Image("manylinux1", "x86_64", "quay.io/pypa/manylinux1_x86_64", None),
    Image("manylinux1", "i686", "quay.io/pypa/manylinux1_i686", None),
    # 2010 images
    Image("manylinux2010", "x86_64", "quay.io/pypa/manylinux2010_x86_64", None),
    Image("manylinux2010", "i686", "quay.io/pypa/manylinux2010_i686", None),
    Image("manylinux2010", "pypy_x86_64", "quay.io/pypa/manylinux2010_x86_64", None),
    Image("manylinux2010", "pypy_i686", "quay.io/pypa/manylinux2010_i686", None),
    # 2014 images
    Image("manylinux2014", "x86_64", "quay.io/pypa/manylinux2014_x86_64", None),
    Image("manylinux2014", "i686", "quay.io/pypa/manylinux2014_i686", None),
    Image("manylinux2014", "aarch64", "quay.io/pypa/manylinux2014_aarch64", None),
    Image("manylinux2014", "ppc64le", "quay.io/pypa/manylinux2014_ppc64le", None),
    Image("manylinux2014", "s390x", "quay.io/pypa/manylinux2014_s390x", None),
    Image("manylinux2014", "pypy_x86_64", "quay.io/pypa/manylinux2014_x86_64", None),
    Image("manylinux2014", "pypy_i686", "quay.io/pypa/manylinux2014_i686", None),
    Image("manylinux2014", "pypy_aarch64", "quay.io/pypa/manylinux2014_aarch64", None),
    # 2_24 images
    Image("manylinux_2_24", "x86_64", "quay.io/pypa/manylinux_2_24_x86_64", None),
    Image("manylinux_2_24", "i686", "quay.io/pypa/manylinux_2_24_i686", None),
    Image("manylinux_2_24", "aarch64", "quay.io/pypa/manylinux_2_24_aarch64", None),
    Image("manylinux_2_24", "ppc64le", "quay.io/pypa/manylinux_2_24_ppc64le", None),
    Image("manylinux_2_24", "s390x", "quay.io/pypa/manylinux_2_24_s390x", None),
    Image("manylinux_2_24", "pypy_x86_64", "quay.io/pypa/manylinux_2_24_x86_64", None),
    Image("manylinux_2_24", "pypy_i686", "quay.io/pypa/manylinux_2_24_i686", None),
    Image("manylinux_2_24", "pypy_aarch64", "quay.io/pypa/manylinux_2_24_aarch64", None),
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

    if not config.has_section(image.platform):
        config[image.platform] = {}

    config[image.platform][image.manylinux_version] = f"{image.image_name}:{tag_name}"

with open(RESOURCES / "pinned_docker_images.cfg", "w") as f:
    config.write(f)
