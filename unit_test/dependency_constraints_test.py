from __future__ import annotations

from pathlib import Path

from cibuildwheel.util.packaging import DependencyConstraints


def test_defaults(tmp_path: Path) -> None:
    dependency_constraints = DependencyConstraints.with_defaults()

    project_root = Path(__file__).parents[1]
    resources_dir = project_root / "cibuildwheel" / "resources"

    assert dependency_constraints.base_file_path
    assert dependency_constraints.base_file_path.samefile(resources_dir / "constraints.txt")
    assert dependency_constraints.get_for_python_version(version="3.99", tmp_dir=tmp_path).samefile(
        resources_dir / "constraints.txt"
    )
    assert dependency_constraints.get_for_python_version(version="3.9", tmp_dir=tmp_path).samefile(
        resources_dir / "constraints-python39.txt"
    )
    assert dependency_constraints.get_for_python_version(version="3.6", tmp_dir=tmp_path).samefile(
        resources_dir / "constraints-python36.txt"
    )


def test_inline_packages(tmp_path: Path) -> None:
    dependency_constraints = DependencyConstraints(
        base_file_path=None,
        packages=["foo==1.2.3", "bar==4.5.6"],
    )

    constraint_file = dependency_constraints.get_for_python_version(version="x.x", tmp_dir=tmp_path)
    constraints_file_contents = constraint_file.read_text()

    assert constraints_file_contents == "foo==1.2.3\nbar==4.5.6"
