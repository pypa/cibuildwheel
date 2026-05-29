from __future__ import annotations

import functools
import tomllib
from pathlib import Path

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Final

    from cibuildwheel.typing import PlatformName

PATH: Final[Path] = Path(__file__).parent.parent / "resources"
INSTALL_CERTIFI_SCRIPT: Final[Path] = PATH / "install_certifi.py"
FREE_THREAD_ENABLE_314: Final[Path] = PATH / "free-threaded-enable-314.xml"
FREE_THREAD_ENABLE_315: Final[Path] = PATH / "free-threaded-enable-315.xml"
NODEJS: Final[Path] = PATH / "nodejs.toml"
DEFAULTS: Final[Path] = PATH / "defaults.toml"
PINNED_DOCKER_IMAGES: Final[Path] = PATH / "pinned_docker_images.cfg"
BUILD_PLATFORMS: Final[Path] = PATH / "build-platforms.toml"
CONSTRAINTS: Final[Path] = PATH / "constraints.txt"
VIRTUALENV: Final[Path] = PATH / "virtualenv.toml"
CIBUILDWHEEL_SCHEMA: Final[Path] = PATH / "cibuildwheel.schema.json"
PYTHON_BUILD_STANDALONE_RELEASES: Final[Path] = PATH / "python-build-standalone-releases.json"
TEST_FAIL_CWD_FILE: Final[Path] = PATH / "testing_temp_dir_file.py"
IOS_SUPPORT_FILES: Final[Path] = PATH / "ios-support"


# this value is cached because it's used a lot in unit tests
@functools.cache
def read_all_configs() -> dict[str, list[dict[str, str]]]:
    with BUILD_PLATFORMS.open("rb") as f:
        loaded_file = tomllib.load(f)
    configs = {k: list[dict[str, str]](v["python_configurations"]) for k, v in loaded_file.items()}
    for platform, python_configs in configs.items():
        for config in python_configs:
            if "url" in config and not config.get("sha256"):
                identifier = config["identifier"]
                msg = f"{platform} Python configuration {identifier!r} is missing a sha256"
                raise ValueError(msg)
    return configs


def read_python_configs(config: PlatformName) -> list[dict[str, str]]:
    return read_all_configs()[config]
