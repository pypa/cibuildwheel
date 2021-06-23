from typing import Dict

import pytest


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--run-emulation", action="store_true", default=False, help="run emulation tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "emulation: mark test requiring qemu binfmt_misc to run")


def pytest_collection_modifyitems(config, items) -> None:
    if config.getoption("--run-emulation"):
        # --run-emulation given in cli: do not skip emulation tests
        return
    skip_emulation = pytest.mark.skip(reason="need --run-emulation option to run")
    for item in items:
        if "emulation" in item.keywords:
            item.add_marker(skip_emulation)


@pytest.fixture(
    params=[{"CIBW_BUILD_FRONTEND": "pip"}, {"CIBW_BUILD_FRONTEND": "build"}], ids=["pip", "build"]
)
def build_frontend_env(request) -> Dict[str, str]:
    return request.param  # type: ignore
