from __future__ import annotations

import subprocess
from test import test_projects

import pytest

from . import utils

basic_project = test_projects.new_c_project()
basic_project.files[
    "repair.py"
] = """
import shutil
import sys
from pathlib import Path

wheel = Path(sys.argv[1])
dest_dir = Path(sys.argv[2])
platform = wheel.stem.split("-")[-1]
name = f"spam-0.1.0-py2-none-{platform}.whl"
dest = dest_dir / name
dest_dir.mkdir(parents=True, exist_ok=True)
if dest.exists():
    dest.unlink()
shutil.copy(wheel, dest)
"""


def test(tmp_path, capfd):
    # this test checks that a generated wheel name shall be unique in a given cibuildwheel run
    project_dir = tmp_path / "project"
    basic_project.generate(project_dir)

    with pytest.raises(subprocess.CalledProcessError):
        utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_REPAIR_WHEEL_COMMAND": "python repair.py {wheel} {dest_dir}",
            },
        )

    captured = capfd.readouterr()
    assert "Build failed because a wheel named" in captured.err
