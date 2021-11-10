import platform as platform_module
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from unittest import mock

import pytest

from cibuildwheel import linux, util
from cibuildwheel.__main__ import main

ALL_IDS = {"cp36", "cp37", "cp38", "cp39", "cp310", "pp37", "pp38"}


@pytest.fixture
def mock_build_docker(monkeypatch):
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
    monkeypatch.setattr("cibuildwheel.linux.DockerContainer", ignore_context_call)

    monkeypatch.setattr("cibuildwheel.linux.build_on_docker", mock.Mock(spec=linux.build_on_docker))
    monkeypatch.setattr("cibuildwheel.util.print_new_wheels", ignore_context_call)


def test_build_default_launches(mock_build_docker, fake_package_dir, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--platform=linux"])

    main()

    build_on_docker = cast(mock.Mock, linux.build_on_docker)

    assert build_on_docker.call_count == 4

    # In Python 3.8+, this can be simplified to [0].kwargs
    kwargs = build_on_docker.call_args_list[0][1]
    assert "quay.io/pypa/manylinux2010_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_x86_64" for x in ALL_IDS}

    kwargs = build_on_docker.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2010_i686" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in ALL_IDS}

    kwargs = build_on_docker.call_args_list[2][1]
    assert "quay.io/pypa/musllinux_1_1_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_x86_64" for x in ALL_IDS for x in ALL_IDS if "pp" not in x
    }

    kwargs = build_on_docker.call_args_list[3][1]
    assert "quay.io/pypa/musllinux_1_1_i686" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_i686" for x in ALL_IDS if "pp" not in x}


def test_build_with_override_launches(mock_build_docker, monkeypatch, tmp_path):
    pkg_dir = tmp_path / "cibw_package"
    pkg_dir.mkdir()

    cibw_toml = pkg_dir / "pyproject.toml"
    cibw_toml.write_text(
        """
[tool.cibuildwheel]
manylinux-x86_64-image = "manylinux2014"

# Before Python 3.10, manylinux2010 is the most compatible
[[tool.cibuildwheel.overrides]]
select = "cp3?-*"
manylinux-x86_64-image = "manylinux2010"
manylinux-i686-image = "manylinux2010"

[[tool.cibuildwheel.overrides]]
select = "cp36-manylinux_x86_64"
before-all = "true"
"""
    )

    monkeypatch.chdir(pkg_dir)
    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--platform=linux"])

    main()

    build_on_docker = cast(mock.Mock, linux.build_on_docker)

    assert build_on_docker.call_count == 6

    kwargs = build_on_docker.call_args_list[0][1]
    assert "quay.io/pypa/manylinux2010_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {"cp36-manylinux_x86_64"}
    assert kwargs["options"].build_options("cp36-manylinux_x86_64").before_all == "true"

    kwargs = build_on_docker.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2010_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-manylinux_x86_64" for x in ALL_IDS - {"cp36", "cp310", "pp37", "pp38"}
    }
    assert kwargs["options"].build_options("cp37-manylinux_x86_64").before_all == ""

    kwargs = build_on_docker.call_args_list[2][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]
    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        "cp310-manylinux_x86_64",
        "pp37-manylinux_x86_64",
        "pp38-manylinux_x86_64",
    }

    kwargs = build_on_docker.call_args_list[3][1]
    assert "quay.io/pypa/manylinux2010_i686" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in ALL_IDS}

    kwargs = build_on_docker.call_args_list[4][1]
    assert "quay.io/pypa/musllinux_1_1_x86_64" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert not kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_x86_64" for x in ALL_IDS for x in ALL_IDS if "pp" not in x
    }

    kwargs = build_on_docker.call_args_list[5][1]
    assert "quay.io/pypa/musllinux_1_1_i686" in kwargs["docker"]["docker_image"]
    assert kwargs["docker"]["cwd"] == Path("/project")
    assert kwargs["docker"]["simulate_32_bit"]

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_i686" for x in ALL_IDS if "pp" not in x}
