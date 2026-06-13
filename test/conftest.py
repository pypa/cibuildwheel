from __future__ import annotations

import dataclasses
import json
import os
import subprocess

import pytest
from filelock import FileLock

from cibuildwheel.architecture import Architecture
from cibuildwheel.ci import detect_ci_provider
from cibuildwheel.options import CommandLineArguments, Options
from cibuildwheel.selector import EnableGroup
from cibuildwheel.typing import PLATFORMS
from cibuildwheel.venv import find_uv

from . import utils
from .utils import DEFAULT_CIBW_ENABLE, EMULATED_ARCHS, get_platform

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator


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


def pytest_configure(config: pytest.Config) -> None:
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


@dataclasses.dataclass(frozen=True)
class DockerWarmUpImage:
    source_name: str
    cached_name: str


@dataclasses.dataclass(frozen=True)
class DockerWarmUpConfig:
    images: list[DockerWarmUpImage]
    env: dict[str, str]


def get_docker_warmup_config(request: pytest.FixtureRequest) -> DockerWarmUpConfig | None:
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
        return None

    options = Options(
        platform="linux",
        command_line_arguments=CommandLineArguments.defaults(),
        env={},
        defaults=True,
    )
    build_options = options.build_options(None)
    assert build_options.manylinux_images is not None
    assert build_options.musllinux_images is not None
    images: list[DockerWarmUpImage] = []
    env: dict[str, str] = {}
    for kind, pinned_images in [
        ("MUSLLINUX", build_options.musllinux_images),
        ("MANYLINUX", build_options.manylinux_images),
    ]:
        for arch in archs:
            source_name = pinned_images[arch]
            cached_name = source_name
            if "@sha256:" in source_name:
                cached_name = source_name.rsplit("@sha256:", 1)[0] + ":cibw_cache_fixture"
                # we change the image name, we will monkeypatch the corresponding environment
                # variable
                for arch_prefix in ["", "PYPY_"]:
                    env[f"CIBW_{kind}_{arch_prefix}{arch.upper()}_IMAGE"] = cached_name
            images.append(DockerWarmUpImage(source_name, cached_name))
    if images:
        return DockerWarmUpConfig(images, env)
    return None


def docker_warmup(config: DockerWarmUpConfig) -> None:
    command = (
        "manylinux-interpreters ensure-all &&"
        "cpython3.13 -m pip download -d /tmp setuptools wheel pytest"
    )
    for image in config.images:
        container_id = subprocess.run(
            ["docker", "create", image.source_name, "bash", "-c", command],
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
                ["docker", "commit", container_id, image.cached_name],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        finally:
            subprocess.run(["docker", "rm", container_id], check=True, stdout=subprocess.DEVNULL)


@pytest.fixture(scope="session", autouse=True)
def docker_warmup_fixture(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory, worker_id: str
) -> Generator[None, None, None]:
    # if we're in CI testing linux, let's warm-up docker images
    if detect_ci_provider() is None or get_platform() != "linux":
        config = None
    elif request.config.getoption("--run-emulation", default=None) is not None:
        # emulation tests only run one test in CI, caching the image only slows down the test
        config = None
    else:
        config = get_docker_warmup_config(request)
    if config is None:
        yield None
        return

    if worker_id == "master":
        # not executing with multiple workers
        # it might be unsafe to write to tmp_path_factory.getbasetemp().parent
        docker_warmup(config)
    else:
        # get the temp directory shared by all workers
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

        fn = root_tmp_dir / "warmup.done"
        with FileLock(str(fn) + ".lock"):
            if not fn.is_file():
                docker_warmup(config)
                fn.write_text("done")

    with pytest.MonkeyPatch.context() as monkeypatch:
        for key, value in config.env.items():
            monkeypatch.setenv(key, value)
        yield None


@pytest.fixture(params=["pip", "build"])
def build_frontend_env_nouv(request: pytest.FixtureRequest) -> dict[str, str]:
    frontend = request.param
    marks = {m.name for m in request.node.iter_markers()}

    platform = "pyodide" if "pyodide" in marks else get_platform()
    if platform == "pyodide" and frontend == "pip":
        pytest.skip("Can't use pip as build frontend for pyodide platform")

    return {"CIBW_BUILD_FRONTEND": frontend}


@pytest.fixture(params=["pip", "build", "build[uv]", "uv"])
def build_frontend_env(request: pytest.FixtureRequest) -> Generator[dict[str, str], None, None]:
    frontend = request.param
    marks = {m.name for m in request.node.iter_markers()}
    if "android" in marks:
        platform = "android"
    elif "ios" in marks:
        platform = "ios"
    elif "pyodide" in marks:
        platform = "pyodide"
    else:
        platform = get_platform()

    if platform in {"pyodide", "ios", "android"} and frontend == "pip":
        pytest.skip(f"Can't use pip as build frontend for {platform}")
    if platform == "pyodide" and frontend in {"build[uv]", "uv"}:
        pytest.skip("Can't use uv with pyodide yet")
    uv_path = find_uv()
    if uv_path is None and frontend in {"build[uv]", "uv"}:
        pytest.skip("Can't find uv, so skipping uv tests")
    if uv_path is not None and frontend == "build" and platform not in {"android", "ios"}:
        pytest.skip("No need to check build when uv is present")

    # temporary workaround: uv doesn't work with graalpy yet
    uses_uv = "uv" in frontend
    env: dict[str, str] = {"CIBW_BUILD_FRONTEND": frontend}
    if uses_uv:
        utils.include_graalpy_in_expected_wheels = False
        env["CIBW_SKIP"] = "gp*"  # skip graalpy when using uv, until uv supports it
    try:
        yield env
    finally:
        if uses_uv:
            utils.include_graalpy_in_expected_wheels = True


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
