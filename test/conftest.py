import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-emulation", action="store_true", default=False, help="run emulation tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "emulation: mark test requiring qemu binfmt_misc to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-emulation"):
        # --run-emulation given in cli: do not skip emulation tests
        return
    skip_emulation = pytest.mark.skip(reason="need --run-emulation option to run")
    for item in items:
        if "emulation" in item.keywords:
            item.add_marker(skip_emulation)
