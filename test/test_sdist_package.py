import shutil
from pathlib import Path

from . import utils


def test(capfd, tmp_path):
    sdist_filename = "spam-0.1.0.tar.gz"
    sdist = Path(__file__).parent / sdist_filename
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # this is a file, not a dir. But that's the variable name used
    package_dir = project_dir / sdist_filename
    shutil.copy2(sdist, package_dir)

    # build the wheels from an sdist
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        package_dir=package_dir,
        add_env={
            # this shouldn't depend on the version of python, so build only CPython 3.6
            "CIBW_BUILD": "cp36-*",
        },
    )

    # check that the expected wheels are produced
    expected_wheels = [w for w in utils.expected_wheels("spam", "0.1.0") if "cp36" in w]
    assert set(actual_wheels) == set(expected_wheels)
