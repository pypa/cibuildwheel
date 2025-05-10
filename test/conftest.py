import json
import os
import subprocess
from collections.abc import Generator

import pytest
from filelock import FileLock

from cibuildwheel.architecture import Architecture
from cibuildwheel.ci import detect_ci_provider
from cibuildwheel.options import CommandLineArguments, Options
from cibuildwheel.selector import EnableGroup
from cibuildwheel.typing import PLATFORMS
from cibuildwheel.venv import find_uv

from .utils import DEFAULT_CIBW_ENABLE, EMULATED_ARCHS, get_platform


def pytest_addoption(parser: pytest.Parser) -> None:
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
    parser.addoption(
        "--enable",
        action="store",
        default=None,
        help="Set the CIBW_ENABLE environment variable for all tests.",
    )
    parser.addoption(
        "--platform",
        action="store",
        default=None,
        help="Set the CIBW_PLATFORM environment variable for all tests.",
    )


def pytest_configure(config):
    flag_enable = config.getoption("--enable")
    flag_platform = config.getoption("--platform")

    if flag_enable is not None and "CIBW_ENABLE" in os.environ:
        msg = (
            "Both --enable pytest option and CIBW_ENABLE environment variable are set. "
            "Please specify only one."
        )
        raise pytest.UsageError(msg)
    if flag_platform is not None and "CIBW_PLATFORM" in os.environ:
        msg = (
            "Both --platform pytest option and CIBW_PLATFORM environment variable are set. "
            "Please specify only one."
        )
        raise pytest.UsageError(msg)

    if flag_enable is not None:
        EnableGroup.parse_option_value(flag_enable)
        os.environ["CIBW_ENABLE"] = flag_enable
    if flag_enable is None and "CIBW_ENABLE" not in os.environ:
        # Set default value for CIBW_ENABLE
        os.environ["CIBW_ENABLE"] = DEFAULT_CIBW_ENABLE

    if flag_platform is not None:
        assert flag_platform in PLATFORMS, f"Invalid platform: {flag_platform}"
        os.environ["CIBW_PLATFORM"] = flag_platform


def docker_warmup(request: pytest.FixtureRequest) -> None:
    machine = request.config.getoption("--run-emulation", default=None)
    if machine is None:
        archs = {arch.value for arch in Architecture.auto_archs("linux")}
    elif machine == "all":
        archs = set(EMULATED_ARCHS)
    else:
        archs = {machine}

    # Only include architectures where there are missing pre-installed interpreters
    archs &= {"x86_64", "i686", "aarch64"}
    if not archs:
        return

    options = Options(
        platform="linux",
        command_line_arguments=CommandLineArguments.defaults(),
        env={},
        defaults=True,
    )
    build_options = options.build_options(None)
    assert build_options.manylinux_images is not None
    assert build_options.musllinux_images is not None
    images = [build_options.manylinux_images[arch] for arch in archs] + [
        build_options.musllinux_images[arch] for arch in archs
    ]
    command = (
        "manylinux-interpreters ensure-all &&"
        "cpython3.13 -m pip download -d /tmp setuptools wheel pytest"
    )
    for image in images:
        container_id = subprocess.run(
            ["docker", "create", image, "bash", "-c", command],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        try:
            subprocess.run(["docker", "start", container_id], check=True, stdout=subprocess.DEVNULL)
            exit_code = subprocess.run(
                ["docker", "wait", container_id], text=True, check=True, stdout=subprocess.PIPE
            ).stdout.strip()
            assert exit_code == "0"
            subprocess.run(
                ["docker", "commit", container_id, image], check=True, stdout=subprocess.DEVNULL
            )
        finally:
            subprocess.run(["docker", "rm", container_id], check=True, stdout=subprocess.DEVNULL)


@pytest.fixture(scope="session", autouse=True)
def docker_warmup_fixture(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory, worker_id: str
) -> None:
    # if we're in CI testing linux, let's warm-up docker images
    if detect_ci_provider() is None or get_platform() != "linux":
        return None
    if request.config.getoption("--run-emulation", default=None) is not None:
        # emulation tests only run one test in CI, caching the image only slows down the test
        return None

    if worker_id == "master":
        # not executing with multiple workers
        # it might be unsafe to write to tmp_path_factory.getbasetemp().parent
        return docker_warmup(request)

    # get the temp directory shared by all workers
    root_tmp_dir = tmp_path_factory.getbasetemp().parent

    fn = root_tmp_dir / "warmup.done"
    with FileLock(str(fn) + ".lock"):
        if not fn.is_file():
            docker_warmup(request)
            fn.write_text("done")
    return None


@pytest.fixture(params=["pip", "build"])
def build_frontend_env_nouv(request: pytest.FixtureRequest) -> dict[str, str]:
    frontend = request.param
    if get_platform() == "pyodide" and frontend == "pip":
        pytest.skip("Can't use pip as build frontend for pyodide platform")

    return {"CIBW_BUILD_FRONTEND": frontend}


@pytest.fixture
def build_frontend_env(build_frontend_env_nouv: dict[str, str]) -> dict[str, str]:
    frontend = build_frontend_env_nouv["CIBW_BUILD_FRONTEND"]
    if frontend != "build" or get_platform() == "pyodide" or find_uv() is None:
        return build_frontend_env_nouv

    return {"CIBW_BUILD_FRONTEND": "build[uv]"}


@pytest.fixture
def docker_cleanup() -> Generator[None, None, None]:
    def get_images() -> set[str]:
        if detect_ci_provider() is None or get_platform() != "linux":
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
