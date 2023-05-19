from __future__ import annotations

import pytest

from . import utils


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--run-emulation", action="store_true", default=False, help="run emulation tests"
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
def build_frontend_env(request) -> dict[str, str]:
    if utils.platform == "pyodide":
        pytest.skip("Can't use pip as build frontend for pyodide platform")
    return request.param  # type: ignore[no-any-return]
