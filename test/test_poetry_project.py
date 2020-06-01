from . import test_projects
from . import utils

pyproject_package_file = """
[tool.poetry]
name = "dummy_package"
version = "0.1.0"
description = "dummy"
authors = ["cibuildwheel poetry test"]
classifiers=[
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
]
license = "MIT"
[tool.poetry.dependencies]
python = ">=2.7"
[tool.poetry.dev-dependencies]
[build-system]
requires = ["poetry>=0.12"]
build-backend = "poetry.masonry.api"
"""

poetry_dummy_project = test_projects.TestProject()
poetry_dummy_project.files["dummy_package/__init__.py"] = ""
poetry_dummy_project.files["pyproject.toml"] = pyproject_package_file


def test_poetry_package(tmp_path):

    # GIVEN a project that only has pyproject.toml
    # managed by poetry
    project_dir = tmp_path / "project"
    poetry_dummy_project.generate(project_dir)

    # Poetry is installed during wheels built by pip
    # however, one of poetry deps require cryptography
    # which fails to build in outdated pip versions
    # more info: https://github.com/pyca/cryptography/issues/5101
    skip_outdated_pip_images_env = {'CIBW_SKIP': 'cp27-* *-win32 *-manylinux_i686 pp*'}

    # WHEN we attempt to build wheels for multiple platforms
    # for dummy_package package
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env=skip_outdated_pip_images_env)

    # THEN we should have a dummy_package wheel with version 0.1.0
    # expected_wheels = utils.expected_wheels("dummy_package", "0.1.0")

    # Workaround while I await maintainers on correct assertion
    expected_wheels = {"dummy_package-0.1.0-py2.py3-none-any.whl"}
    assert set(actual_wheels) == set(expected_wheels)
