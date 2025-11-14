import subprocess
import textwrap
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
if platform.startswith("pyodide"):
    # for the sake of this test, munge the pyodide platforms into one, it's
    # not valid, but it does activate the uniqueness check
    platform = "pyodide"

name = f"spam-0.1.0-py2-none-{platform}.whl"
dest = dest_dir / name
dest_dir.mkdir(parents=True, exist_ok=True)
dest.unlink(missing_ok=True)
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
        # We only produced one wheel (perhaps Pyodide)
        # check that it has the right name
        assert result[0].startswith("spam-0.1.0-py2-none-")


@pytest.mark.parametrize(
    "repair_command",
    [
        "python repair.py {wheel} {dest_dir}",
        "python {package}/repair.py {wheel} {dest_dir}",
        "python {project}/repair.py {wheel} {dest_dir}",
    ],
    ids=["no-placeholder", "package-placeholder", "project-placeholder"],
)
def test_repair_wheel_command_structure(tmp_path, repair_command):
    project_dir = tmp_path / "project"
    project = test_projects.new_c_project()
    project.files["repair.py"] = textwrap.dedent("""
        import shutil
        import sys
        from pathlib import Path

        wheel = Path(sys.argv[1])
        dest_dir = Path(sys.argv[2])

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(wheel, dest_dir / "spamrepaired-0.0.1-py-none-any.whl")
    """)

    # Combined test for repair wheel command formats (plain, {package}, {project})
    project.generate(project_dir)

    result = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_REPAIR_WHEEL_COMMAND": repair_command,
            "CIBW_ARCHS": "native",
        },
        single_python=True,
    )

    assert result == ["spamrepaired-0.0.1-py-none-any.whl"]
