from textwrap import dedent

from cibuildwheel.projectfiles import get_requires_python_str, setup_py_python_requires


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
    assert get_requires_python_str(tmp_path) == "1.23"


def test_read_setup_py_full(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(
            dedent(
                """
                import setuptools

                setuptools.randomfunc()

                setuptools.setup(
                    name = "hello",
                    other = 23,
                    example = ["item", "other"],
                    python_requires = "1.24",
                )
                """
            )
        )

    assert setup_py_python_requires(tmp_path.joinpath("setup.py").read_text()) == "1.24"
    assert get_requires_python_str(tmp_path) == "1.24"


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
    assert get_requires_python_str(tmp_path) is None


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
    assert get_requires_python_str(tmp_path) is None


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
    assert get_requires_python_str(tmp_path) is None


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

    assert get_requires_python_str(tmp_path) == "1.234"


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

    assert get_requires_python_str(tmp_path) is None


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

    assert get_requires_python_str(tmp_path) == "1.654"


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

    assert get_requires_python_str(tmp_path) is None
