import functools
import tomllib
from pathlib import Path
from typing import Final

from ..typing import PlatformName

PATH: Final[Path] = Path(__file__).parent.parent / "resources"
INSTALL_CERTIFI_SCRIPT: Final[Path] = PATH / "install_certifi.py"
FREE_THREAD_ENABLE_313: Final[Path] = PATH / "free-threaded-enable-313.xml"
FREE_THREAD_ENABLE_314: Final[Path] = PATH / "free-threaded-enable-314.xml"
NODEJS: Final[Path] = PATH / "nodejs.toml"
DEFAULTS: Final[Path] = PATH / "defaults.toml"
PINNED_DOCKER_IMAGES: Final[Path] = PATH / "pinned_docker_images.cfg"
BUILD_PLATFORMS: Final[Path] = PATH / "build-platforms.toml"
CONSTRAINTS: Final[Path] = PATH / "constraints.txt"
VIRTUALENV: Final[Path] = PATH / "virtualenv.toml"
CIBUILDWHEEL_SCHEMA: Final[Path] = PATH / "cibuildwheel.schema.json"
PYTHON_BUILD_STANDALONE_RELEASES: Final[Path] = PATH / "python-build-standalone-releases.json"
TEST_FAIL_CWD_FILE: Final[Path] = PATH / "testing_temp_dir_file.py"


# this value is cached because it's used a lot in unit tests
@functools.cache
def read_python_configs(config: PlatformName) -> list[dict[str, str]]:
    with BUILD_PLATFORMS.open("rb") as f:
        loaded_file = tomllib.load(f)
    results: list[dict[str, str]] = list(loaded_file[config]["python_configurations"])
    return results
