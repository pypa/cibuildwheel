import sys
from pathlib import Path

import pytest

MOCK_PACKAGE_DIR = Path("some_package_dir")


def pytest_addoption(parser):
    parser.addoption("--run-docker", action="store_true", default=False, help="run docker tests")
    parser.addoption("--run-podman", action="store_true", default=False, help="run podman tests")
    parser.addoption(
        "--run-cp38-universal2",
        action="store_true",
        default=False,
        help="macOS cp38 uses the universal2 installer",
    )


@pytest.fixture
def fake_package_dir(tmp_path, monkeypatch):
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
    tmp_path.joinpath(MOCK_PACKAGE_DIR).mkdir()
    monkeypatch.setattr(Path, "exists", mock_path_exists)
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.chdir(tmp_path)
    return args
