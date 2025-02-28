import sys
import textwrap

import pytest
from packaging.specifiers import SpecifierSet

from cibuildwheel.__main__ import main


@pytest.fixture(autouse=True)
def fake_package_dir(monkeypatch, tmp_path):
    """
    Set up a fake project
    """

    local_path = tmp_path / "tmp_project"
    local_path.mkdir()

    local_path.joinpath("setup.py").touch()

    monkeypatch.setattr(sys, "argv", ["cibuildwheel", str(local_path)])

    return local_path


@pytest.mark.usefixtures("platform")
def test_no_override(intercepted_build_args):
    main()

    options = intercepted_build_args.args[0]
    intercepted_build_selector = options.globals.build_selector

    assert intercepted_build_selector("cp39-win32")
    assert intercepted_build_selector("cp36-win32")

    assert intercepted_build_selector.requires_python is None


@pytest.mark.usefixtures("platform")
def test_override_env(monkeypatch, intercepted_build_args):
    monkeypatch.setenv("CIBW_PROJECT_REQUIRES_PYTHON", ">=3.8")

    main()

    options = intercepted_build_args.args[0]
    intercepted_build_selector = options.globals.build_selector

    assert intercepted_build_selector.requires_python == SpecifierSet(">=3.8")

    assert intercepted_build_selector("cp39-win32")
    assert not intercepted_build_selector("cp36-win32")


@pytest.mark.usefixtures("platform")
def test_override_setup_cfg(intercepted_build_args, fake_package_dir):
    fake_package_dir.joinpath("setup.cfg").write_text(
        textwrap.dedent(
            """
            [options]
            python_requires = >=3.8
            """
        )
    )

    main()

    options = intercepted_build_args.args[0]
    intercepted_build_selector = options.globals.build_selector

    assert intercepted_build_selector.requires_python == SpecifierSet(">=3.8")

    assert intercepted_build_selector("cp39-win32")
    assert not intercepted_build_selector("cp36-win32")


@pytest.mark.usefixtures("platform")
def test_override_pyproject_toml(intercepted_build_args, fake_package_dir):
    fake_package_dir.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            requires-python = ">=3.8"
            """
        )
    )

    main()

    options = intercepted_build_args.args[0]
    intercepted_build_selector = options.globals.build_selector

    assert intercepted_build_selector.requires_python == SpecifierSet(">=3.8")

    assert intercepted_build_selector("cp39-win32")
    assert not intercepted_build_selector("cp36-win32")


@pytest.mark.usefixtures("platform")
def test_override_setup_py_simple(intercepted_build_args, fake_package_dir):
    fake_package_dir.joinpath("setup.py").write_text(
        textwrap.dedent(
            """
            from setuptools import setup

            setup(
                name = "other",
                python_requires = ">=3.7",
            )
            """
        )
    )

    main()

    options = intercepted_build_args.args[0]
    intercepted_build_selector = options.globals.build_selector

    assert intercepted_build_selector.requires_python == SpecifierSet(">=3.7")

    assert intercepted_build_selector("cp39-win32")
    assert not intercepted_build_selector("cp36-win32")
