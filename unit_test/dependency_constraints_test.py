from pathlib import Path

from cibuildwheel.util import DependencyConstraints


def test_defaults():
    dependency_constraints = DependencyConstraints.with_defaults()

    project_root = Path(__file__).parents[1]
    resources_dir = project_root / 'cibuildwheel' / 'resources'

    assert dependency_constraints.base_file_path.samefile(resources_dir / 'constraints.txt')
    assert dependency_constraints.get_for_python_version('3.99').samefile(resources_dir / 'constraints.txt')
    assert dependency_constraints.get_for_python_version('3.9').samefile(resources_dir / 'constraints-python39.txt')
    assert dependency_constraints.get_for_python_version('3.6').samefile(resources_dir / 'constraints-python36.txt')
    assert dependency_constraints.get_for_python_version('3.5').samefile(resources_dir / 'constraints-python35.txt')
    assert dependency_constraints.get_for_python_version('2.7').samefile(resources_dir / 'constraints-python27.txt')
