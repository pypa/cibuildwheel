from __future__ import annotations

import platform as platform_module
import subprocess
import sys
from contextlib import contextmanager
from pathlib import PurePosixPath
from typing import cast
from unittest import mock

import pytest

from cibuildwheel import linux, util
from cibuildwheel.__main__ import main

ALL_IDS = {"cp36", "cp37", "cp38", "cp39", "cp310", "cp311", "pp37", "pp38", "pp39"}


@pytest.fixture
def mock_build_container(monkeypatch):
    def fail_on_call(*args, **kwargs):
        raise RuntimeError("This should never be called")

    def ignore_call(*args, **kwargs):
        pass

    @contextmanager
    def nullcontext(enter_result=None):
        yield enter_result

    def ignore_context_call(*args, **kwargs):
        return nullcontext(kwargs)

    monkeypatch.setenv("CIBW_PLATFORM", "linux")
    monkeypatch.setattr(platform_module, "machine", lambda: "x86_64")

    monkeypatch.setattr(subprocess, "Popen", fail_on_call)
    monkeypatch.setattr(subprocess, "run", ignore_call)
    monkeypatch.setattr(util, "download", fail_on_call)
    monkeypatch.setattr("cibuildwheel.linux.OCIContainer", ignore_context_call)

    monkeypatch.setattr(
        "cibuildwheel.linux.build_in_container", mock.Mock(spec=linux.build_in_container)
    )
    monkeypatch.setattr("cibuildwheel.util.print_new_wheels", ignore_context_call)


def test_build_default_launches(mock_build_container, fake_package_dir, monkeypatch):
    monkeypatch.setattr(sys, "argv", sys.argv + ["--platform=linux"])

    main()

    build_in_container = cast(mock.Mock, linux.build_in_container)

    assert build_in_container.call_count == 4

    # In Python 3.8+, this can be simplified to [0].kwargs
    kwargs = build_in_container.call_args_list[0][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_x86_64" for x in ALL_IDS}

    kwargs = build_in_container.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2014_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in ALL_IDS}

    kwargs = build_in_container.call_args_list[2][1]
    assert "quay.io/pypa/musllinux_1_1_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_x86_64" for x in ALL_IDS for x in ALL_IDS if "pp" not in x
    }

    kwargs = build_in_container.call_args_list[3][1]
    assert "quay.io/pypa/musllinux_1_1_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_i686" for x in ALL_IDS if "pp" not in x}


def test_build_with_override_launches(mock_build_container, monkeypatch, tmp_path):
    pkg_dir = tmp_path / "cibw_package"
    pkg_dir.mkdir()

    cibw_toml = pkg_dir / "pyproject.toml"
    cibw_toml.write_text(
        """
[tool.cibuildwheel]
manylinux-x86_64-image = "manylinux_2_24"

# Before Python 3.10, use manylinux2014
[[tool.cibuildwheel.overrides]]
select = "cp3?-*"
manylinux-x86_64-image = "manylinux2014"
manylinux-i686-image = "manylinux2014"

[[tool.cibuildwheel.overrides]]
select = "cp36-manylinux_x86_64"
before-all = "true"
"""
    )

    monkeypatch.chdir(pkg_dir)
    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--platform=linux"])

    main()

    build_in_container = cast(mock.Mock, linux.build_in_container)

    assert build_in_container.call_count == 6

    kwargs = build_in_container.call_args_list[0][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {"cp36-manylinux_x86_64"}
    assert kwargs["options"].build_options("cp36-manylinux_x86_64").before_all == "true"

    kwargs = build_in_container.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-manylinux_x86_64"
        for x in ALL_IDS - {"cp36", "cp310", "cp311", "pp37", "pp38", "pp39"}
    }
    assert kwargs["options"].build_options("cp37-manylinux_x86_64").before_all == ""

    kwargs = build_in_container.call_args_list[2][1]
    assert "quay.io/pypa/manylinux_2_24_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]
    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-manylinux_x86_64" for x in {"cp310", "cp311", "pp37", "pp38", "pp39"}
    }

    kwargs = build_in_container.call_args_list[3][1]
    assert "quay.io/pypa/manylinux2014_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in ALL_IDS}

    kwargs = build_in_container.call_args_list[4][1]
    assert "quay.io/pypa/musllinux_1_1_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert not kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_x86_64" for x in ALL_IDS for x in ALL_IDS if "pp" not in x
    }

    kwargs = build_in_container.call_args_list[5][1]
    assert "quay.io/pypa/musllinux_1_1_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_i686" for x in ALL_IDS if "pp" not in x}
