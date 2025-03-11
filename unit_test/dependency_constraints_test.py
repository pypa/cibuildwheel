from pathlib import Path

import pytest

from cibuildwheel.util.packaging import DependencyConstraints


def test_defaults(tmp_path: Path) -> None:
    dependency_constraints = DependencyConstraints.pinned()

    project_root = Path(__file__).parents[1]
    resources_dir = project_root / "cibuildwheel" / "resources"

    assert dependency_constraints.base_file_path
    assert dependency_constraints.base_file_path.samefile(resources_dir / "constraints.txt")

    constraints_file = dependency_constraints.get_for_python_version(
        version="3.99", tmp_dir=tmp_path
    )
    assert constraints_file
    assert constraints_file.samefile(resources_dir / "constraints.txt")

    constraints_file = dependency_constraints.get_for_python_version(
        version="3.9", tmp_dir=tmp_path
    )
    assert constraints_file
    assert constraints_file.samefile(resources_dir / "constraints-python39.txt")

    constraints_file = dependency_constraints.get_for_python_version(
        version="3.13", tmp_dir=tmp_path
    )
    assert constraints_file
    assert constraints_file.samefile(resources_dir / "constraints-python313.txt")


def test_inline_packages(tmp_path: Path) -> None:
    dependency_constraints = DependencyConstraints(
        base_file_path=None,
        packages=["foo==1.2.3", "bar==4.5.6"],
    )

    constraint_file = dependency_constraints.get_for_python_version(version="x.x", tmp_dir=tmp_path)
    assert constraint_file
    constraints_file_contents = constraint_file.read_text()

    assert constraints_file_contents == "foo==1.2.3\nbar==4.5.6"


@pytest.mark.parametrize("config_string", ["", "latest", "packages:"])
def test_empty_constraints(config_string: str) -> None:
    dependency_constraints = DependencyConstraints.from_config_string(config_string)

    assert not dependency_constraints.packages
    assert not dependency_constraints.base_file_path
    assert dependency_constraints == DependencyConstraints.latest()
