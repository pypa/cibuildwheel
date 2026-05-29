import importlib.util
from pathlib import Path

import pytest
from packaging.specifiers import Specifier
from packaging.version import Version

from cibuildwheel.util import resources


def test_url_based_python_configs_have_sha256() -> None:
    for python_configurations in resources.read_all_configs().values():
        for config in python_configurations:
            if "url" in config:
                assert config["sha256"]


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


def test_graalpy_uses_latest_release_with_matching_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_path = Path(__file__).resolve().parents[1] / "bin" / "update_pythons.py"
    spec = importlib.util.spec_from_file_location("update_pythons", script_path)
    if spec is None or spec.loader is None:
        pytest.fail(f"Failed to load {script_path}")
    update_pythons = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(update_pythons)

    graalpy = object.__new__(update_pythons.GraalPyVersions)
    graalpy.releases = [
        {
            "tag_name": "graal-25.0.1",
            "graalpy_version": Version("25.0.1"),
            "python_version": Version("3.12"),
            "assets": [
                {
                    "name": "graalpy-25.0.1-macos-amd64.tar.gz",
                    "browser_download_url": "https://example.invalid/graalpy-25.0.1-macos-amd64.tar.gz",
                },
                {
                    "name": "graalpy-25.0.1-macos-amd64.tar.gz.sha256",
                    "browser_download_url": "https://example.invalid/graalpy-25.0.1-macos-amd64.tar.gz.sha256",
                },
            ],
        },
        {
            "tag_name": "graal-25.0.3",
            "graalpy_version": Version("25.0.3"),
            "python_version": Version("3.12"),
            "assets": [],
        },
    ]

    def fake_get(url: str, **_kwargs: object) -> _Response:
        assert url == "https://example.invalid/graalpy-25.0.1-macos-amd64.tar.gz.sha256"
        return _Response("deadbeef  graalpy-25.0.1-macos-amd64.tar.gz\n")

    monkeypatch.setattr(update_pythons.requests, "get", fake_get)

    config = graalpy.update_version("gp312_250-macosx_x86_64", Specifier("==3.12.*"))

    assert config == {
        "identifier": "gp312_250-macosx_x86_64",
        "version": "3.12",
        "url": "https://example.invalid/graalpy-25.0.1-macos-amd64.tar.gz",
        "sha256": "deadbeef",
    }
