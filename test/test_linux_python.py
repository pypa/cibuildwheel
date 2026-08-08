from __future__ import annotations

import os
import platform
import subprocess

import pytest

from . import test_projects, utils

TYPE_CHECKING = False
if TYPE_CHECKING:
    from pathlib import Path


def test_python_exist(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    if utils.get_platform() != "linux":
        pytest.skip("the test is only relevant to the linux build")
    if os.environ.get("CIBW_CONTAINER_ENGINE", "docker") == "none":
        pytest.skip("the test is only relevant for CIBW_CONTAINER_ENGINE != 'none'")
    machine = platform.machine()
    if machine not in ["x86_64", "i686"]:
        pytest.skip(
            "this test is currently only possible on x86_64/i686 due to availability of alternative images"
        )

    project_dir = tmp_path / "project"
    basic_project = test_projects.new_c_project()
    basic_project.generate(project_dir)

    image = f"quay.io/pypa/manylinux2010_{machine}:2022-08-05-4535177"

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_MANYLINUX_X86_64_IMAGE": image,
                "CIBW_MANYLINUX_I686_IMAGE": image,
                "CIBW_BUILD": "cp3{10,11}-manylinux*",
            },
        )

    captured = capfd.readouterr()
    print("out", captured.out)
    print("err", captured.err)
    assert f" to build 'cp310-manylinux_{machine}'." not in captured.err
    message = (
        "'/opt/python/cp311-cp311/bin/python' executable doesn't exist"
        f" in image '{image}' to build 'cp311-manylinux_{machine}'."
    )
    assert message in captured.err
