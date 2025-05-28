import platform as platform_module
import subprocess
import sys
import typing
from contextlib import contextmanager
from pathlib import PurePosixPath
from unittest import mock

import pytest

from cibuildwheel import platforms
from cibuildwheel.__main__ import main
from cibuildwheel.oci_container import OCIPlatform
from cibuildwheel.util import file

DEFAULT_IDS = {"cp38", "cp39", "cp310", "cp311", "cp312", "cp313"}
ALL_IDS = DEFAULT_IDS | {"cp313t", "pp38", "pp39", "pp310", "pp311", "gp311_242"}


@pytest.fixture
def mock_build_container(monkeypatch):
    def fail_on_call(*args, **kwargs):
        msg = "This should never be called"
        raise RuntimeError(msg)

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
    monkeypatch.setattr(file, "download", fail_on_call)
    monkeypatch.setattr("cibuildwheel.platforms.linux.OCIContainer", ignore_context_call)

    monkeypatch.setattr(
        "cibuildwheel.platforms.linux.build_in_container",
        mock.Mock(spec=platforms.linux.build_in_container),
    )
    monkeypatch.setattr("cibuildwheel.__main__.print_new_wheels", ignore_context_call)


@pytest.mark.usefixtures("mock_build_container", "fake_package_dir")
def test_build_default_launches(monkeypatch):
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--platform=linux"])
    monkeypatch.delenv("CIBW_ENABLE", raising=False)

    main()

    build_in_container = typing.cast(mock.Mock, platforms.linux.build_in_container)

    assert build_in_container.call_count == 4

    # In Python 3.8+, this can be simplified to [0].kwargs
    kwargs = build_in_container.call_args_list[0][1]
    assert "quay.io/pypa/manylinux_2_28_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_x86_64" for x in DEFAULT_IDS}

    kwargs = build_in_container.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2014_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.i386

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in DEFAULT_IDS}

    kwargs = build_in_container.call_args_list[2][1]
    assert "quay.io/pypa/musllinux_1_2_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_x86_64" for x in DEFAULT_IDS}

    kwargs = build_in_container.call_args_list[3][1]
    assert "quay.io/pypa/musllinux_1_2_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.i386

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-musllinux_i686" for x in DEFAULT_IDS}


@pytest.mark.usefixtures("mock_build_container")
def test_build_with_override_launches(monkeypatch, tmp_path):
    pkg_dir = tmp_path / "cibw_package"
    pkg_dir.mkdir()

    cibw_toml = pkg_dir / "pyproject.toml"
    cibw_toml.write_text(
        """
[tool.cibuildwheel]
manylinux-x86_64-image = "manylinux_2_28"
musllinux-x86_64-image = "musllinux_1_2"
enable = ["pypy", "pypy-eol", "graalpy", "cpython-freethreading"]

# Before Python 3.10, use manylinux2014
[[tool.cibuildwheel.overrides]]
select = "cp3?-*"
manylinux-x86_64-image = "manylinux2014"
manylinux-i686-image = "manylinux2014"

[[tool.cibuildwheel.overrides]]
select = "cp38-manylinux_x86_64"
before-all = "true"
"""
    )

    monkeypatch.chdir(pkg_dir)
    monkeypatch.setattr(sys, "argv", ["cibuildwheel", "--platform=linux"])
    monkeypatch.delenv("CIBW_ENABLE", raising=False)

    main()

    build_in_container = typing.cast(mock.Mock, platforms.linux.build_in_container)

    assert build_in_container.call_count == 6

    kwargs = build_in_container.call_args_list[0][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {"cp38-manylinux_x86_64"}
    assert kwargs["options"].build_options("cp38-manylinux_x86_64").before_all == "true"

    kwargs = build_in_container.call_args_list[1][1]
    assert "quay.io/pypa/manylinux2014_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-manylinux_x86_64"
        for x in ALL_IDS
        - {
            "cp38",
            "cp310",
            "cp311",
            "cp312",
            "cp313",
            "cp313t",
            "pp38",
            "pp39",
            "pp310",
            "pp311",
            "gp311_242",
        }
    }
    assert kwargs["options"].build_options("cp39-manylinux_x86_64").before_all == ""

    kwargs = build_in_container.call_args_list[2][1]
    assert "quay.io/pypa/manylinux_2_28_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64
    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-manylinux_x86_64"
        for x in [
            "cp310",
            "cp311",
            "cp312",
            "cp313",
            "cp313t",
            "pp38",
            "pp39",
            "pp310",
            "pp311",
            "gp311_242",
        ]
    }

    kwargs = build_in_container.call_args_list[3][1]
    assert "quay.io/pypa/manylinux2014_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.i386

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {f"{x}-manylinux_i686" for x in ALL_IDS if "gp" not in x}

    kwargs = build_in_container.call_args_list[4][1]
    assert "quay.io/pypa/musllinux_1_2_x86_64" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.AMD64
    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_x86_64" for x in ALL_IDS if "pp" not in x and "gp" not in x
    }

    kwargs = build_in_container.call_args_list[5][1]
    assert "quay.io/pypa/musllinux_1_2_i686" in kwargs["container"]["image"]
    assert kwargs["container"]["cwd"] == PurePosixPath("/project")
    assert kwargs["container"]["oci_platform"] == OCIPlatform.i386

    identifiers = {x.identifier for x in kwargs["platform_configs"]}
    assert identifiers == {
        f"{x}-musllinux_i686" for x in ALL_IDS if "pp" not in x and "gp" not in x
    }
