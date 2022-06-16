import sys
from pathlib import Path

import pytest

MOCK_PACKAGE_DIR = Path("some_package_dir")


def pytest_addoption(parser):
    parser.addoption("--run-docker", action="store_true", default=False, help="run docker tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: mark test requiring docker to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-docker"):
        # --run-docker given in cli: do not skip container tests
        return
    skip_docker = pytest.mark.skip(reason="need --run-docker option to run")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip_docker)


@pytest.fixture
def fake_package_dir(monkeypatch):
    """
    Monkey-patch enough for the main() function to run
    """
    real_path_exists = Path.exists

    def mock_path_exists(path):
        if str(path).endswith(str(MOCK_PACKAGE_DIR / "setup.py")):
            return True
        else:
            return real_path_exists(path)

    args = ["cibuildwheel", str(MOCK_PACKAGE_DIR)]
    monkeypatch.setattr(Path, "exists", mock_path_exists)
    monkeypatch.setattr(sys, "argv", args)
    return args
