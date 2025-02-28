import tomllib
from textwrap import dedent

import pytest

from cibuildwheel.projectfiles import (
    get_requires_python_str,
    resolve_dependency_groups,
    setup_py_python_requires,
)


def test_read_setup_py_simple(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                setup(
                    name = "hello",
                    other = 23,
                    example = ["item", "other"],
                    python_requires = "1.23",
                )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) == "1.23"
    assert get_requires_python_str(tmp_path, {}) == "1.23"


def test_read_setup_py_if_main(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                if __name__ == "__main__":
                    setup(
                        name = "hello",
                        other = 23,
                        example = ["item", "other"],
                        python_requires = "1.23",
                    )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) == "1.23"
    assert get_requires_python_str(tmp_path, {}) == "1.23"


def test_read_setup_py_if_main_reversed(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                if "__main__" == __name__:
                    setup(
                        name = "hello",
                        other = 23,
                        example = ["item", "other"],
                        python_requires = "1.23",
                    )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) == "1.23"
    assert get_requires_python_str(tmp_path, {}) == "1.23"


def test_read_setup_py_if_invalid(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                if True:
                    setup(
                        name = "hello",
                        other = 23,
                        example = ["item", "other"],
                        python_requires = "1.23",
                    )
                """
            )
        )

    assert not setup_py_python_requires(tmp_path.joinpath("setup.py").read_text())
    assert not get_requires_python_str(tmp_path, {})


def test_read_setup_py_full(tmp_path):
    with open(tmp_path / "setup.py", "w", encoding="utf8") as f:
        f.write(
            dedent(
                """
                import setuptools

                setuptools.randomfunc()

                setuptools.setup(
                    name = "hello",
                    description = "≥“”ü",
                    other = 23,
                    example = ["item", "other"],
                    python_requires = "1.24",
                )
                """
            )
        )

    assert (
        setup_py_python_requires(tmp_path.joinpath("setup.py").read_text(encoding="utf8")) == "1.24"
    )
    assert get_requires_python_str(tmp_path, {}) == "1.24"


def test_read_setup_py_assign(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                REQUIRES = "3.21"

                setuptools.setup(
                    name = "hello",
                    other = 23,
                    example = ["item", "other"],
                    python_requires = REQUIRES,
                )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) is None
    assert get_requires_python_str(tmp_path, {}) is None


def test_read_setup_py_None(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                REQUIRES = None

                setuptools.setup(
                    name = "hello",
                    other = 23,
                    example = ["item", "other"],
                    python_requires = None,
                )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) is None
    assert get_requires_python_str(tmp_path, {}) is None


def test_read_setup_py_empty(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                from setuptools import setup

                REQUIRES = "3.21"

                setuptools.setup(
                    name = "hello",
                    other = 23,
                    example = ["item", "other"],
                )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) is None
    assert get_requires_python_str(tmp_path, {}) is None


def test_read_setup_cfg(tmp_path):
    with open(tmp_path / "setup.cfg", "w") as f:
        f.write(
            dedent(
                """
                [options]
                python_requires = 1.234
                [metadata]
                something = other
                """
            )
        )

    assert get_requires_python_str(tmp_path, {}) == "1.234"


def test_read_setup_cfg_empty(tmp_path):
    with open(tmp_path / "setup.cfg", "w") as f:
        f.write(
            dedent(
                """
                [options]
                other = 1.234
                [metadata]
                something = other
                """
            )
        )

    assert get_requires_python_str(tmp_path, {}) is None


def test_read_pyproject_toml(tmp_path):
    with open(tmp_path / "pyproject.toml", "w") as f:
        f.write(
            dedent(
                """
                [project]
                requires-python = "1.654"

                [tool.cibuildwheel]
                something = "other"
                """
            )
        )
    with open(tmp_path / "pyproject.toml", "rb") as f:
        pyproject_toml = tomllib.load(f)

    assert get_requires_python_str(tmp_path, pyproject_toml) == "1.654"


def test_read_pyproject_toml_empty(tmp_path):
    with open(tmp_path / "pyproject.toml", "w") as f:
        f.write(
            dedent(
                """
                [project]
                other = 1.234
                """
            )
        )
    with open(tmp_path / "pyproject.toml", "rb") as f:
        pyproject_toml = tomllib.load(f)

    assert get_requires_python_str(tmp_path, pyproject_toml) is None


def test_read_dep_groups():
    pyproject_toml = {"dependency-groups": {"group1": ["pkg1", "pkg2"], "group2": ["pkg3"]}}
    assert resolve_dependency_groups(pyproject_toml) == ()
    assert resolve_dependency_groups(pyproject_toml, "group1") == ("pkg1", "pkg2")
    assert resolve_dependency_groups(pyproject_toml, "group2") == ("pkg3",)
    assert resolve_dependency_groups(pyproject_toml, "group1", "group2") == ("pkg1", "pkg2", "pkg3")


def test_dep_group_no_file_error():
    with pytest.raises(FileNotFoundError, match=r"pyproject\.toml"):
        resolve_dependency_groups(None, "test")


def test_dep_group_no_section_error():
    with pytest.raises(KeyError, match=r"pyproject\.toml"):
        resolve_dependency_groups({}, "test")
