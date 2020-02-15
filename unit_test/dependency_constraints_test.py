from cibuildwheel.util import DependencyConstraints
import os


def test_defaults():
    dependency_constraints = DependencyConstraints.with_defaults()

    project_root = os.path.dirname(os.path.dirname(__file__))
    resources_dir = os.path.join(project_root, 'cibuildwheel', 'resources')

    assert os.path.samefile(
        dependency_constraints.base_file_path,
        os.path.join(resources_dir, 'constraints.txt')
    )
    assert os.path.samefile(
        dependency_constraints.get_for_python_version('3.8'),
        os.path.join(resources_dir, 'constraints.txt')
    )
    assert os.path.samefile(
        dependency_constraints.get_for_python_version('2.7'),
        os.path.join(resources_dir, 'constraints-python27.txt')
    )
