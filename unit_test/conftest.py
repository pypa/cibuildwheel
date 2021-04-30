import pytest


def pytest_addoption(parser):
    parser.addoption("--run-docker", action="store_true", default=False, help="run docker tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: mark test requiring docker to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-docker"):
        # --run-docker given in cli: do not skip docker tests
        return
    skip_docker = pytest.mark.skip(reason="need --run-docker option to run")
    for item in items:
        if "docker" in item.keywords:
            item.add_marker(skip_docker)
