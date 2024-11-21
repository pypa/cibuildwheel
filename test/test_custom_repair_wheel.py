from __future__ import annotations

import subprocess
from contextlib import nullcontext as does_not_raise

import pytest

from test import test_projects

from . import utils

basic_project = test_projects.new_c_project()
basic_project.files["repair.py"] = """
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

    num_builds = len(utils.cibuildwheel_get_build_identifiers(project_dir))
    expectation = (
        pytest.raises(subprocess.CalledProcessError) if num_builds > 1 else does_not_raise()
    )

    with expectation as exc_info:
        result = utils.cibuildwheel_run(
            project_dir,
            add_env={
                "CIBW_REPAIR_WHEEL_COMMAND": "python repair.py {wheel} {dest_dir}",
            },
        )

    captured = capfd.readouterr()
    if num_builds > 1:
        assert exc_info is not None
        assert "Build failed because a wheel named" in captured.err
        assert exc_info.value.returncode == 6
    else:
        # We only produced one wheel (currently Pyodide)
        # check that it has the right name
        #
        # As far as I can tell, this is the only full test coverage for
        # CIBW_REPAIR_WHEEL_COMMAND so this is useful even in the case when no
        # error is raised
        assert "spam-0.1.0-py2-none-pyodide" in captured.out
        assert result[0].startswith("spam-0.1.0-py2-none-")
