from __future__ import annotations

import json
import subprocess
from typing import Generator

import pytest

from cibuildwheel.util import detect_ci_provider, find_uv

from .utils import EMULATED_ARCHS, platform


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--run-emulation",
        action="store",
        default=None,
        help="run emulation tests",
        choices=("all", *EMULATED_ARCHS),
    )
    parser.addoption("--run-podman", action="store_true", default=False, help="run podman tests")
    parser.addoption(
        "--run-cp38-universal2",
        action="store_true",
        default=False,
        help="macOS cp38 uses the universal2 installer",
    )


@pytest.fixture(
    params=[{"CIBW_BUILD_FRONTEND": "pip"}, {"CIBW_BUILD_FRONTEND": "build"}], ids=["pip", "build"]
)
def build_frontend_env_nouv(request) -> dict[str, str]:
    if platform == "pyodide":
        pytest.skip("Can't use pip as build frontend for pyodide platform")

    return request.param  # type: ignore[no-any-return]


@pytest.fixture()
def build_frontend_env(build_frontend_env_nouv: dict[str, str]) -> dict[str, str]:
    if build_frontend_env_nouv["CIBW_BUILD_FRONTEND"] == "build" and find_uv() is not None:
        return {"CIBW_BUILD_FRONTEND": "build[uv]"}

    return build_frontend_env_nouv


@pytest.fixture()
def docker_cleanup() -> Generator[None, None, None]:
    def get_images() -> set[str]:
        if detect_ci_provider() is None or platform != "linux":
            return set()
        images = subprocess.run(
            ["docker", "image", "ls", "--format", "{{json .ID}}"],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        return {json.loads(image.strip()) for image in images.splitlines() if image.strip()}

    images_before = get_images()
    try:
        yield
    finally:
        images_after = get_images()
        for image in images_after - images_before:
            subprocess.run(["docker", "rmi", image], check=False)
