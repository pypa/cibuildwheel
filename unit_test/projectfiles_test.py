from textwrap import dedent

from cibuildwheel.projectfiles import ProjectFiles, dig


def test_read_setup_py_simple(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(dedent("""
            from setuptools import setup

            setup(
                name = "hello",
                other = 23,
                example = ["item", "other"],
                python_requires = "1.23",
            )
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files._setup_py_python_requires() == "1.23"
    assert project_files.get_requires_python_str() == "1.23"


def test_read_setup_py_full(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(dedent("""
            import setuptools

            setuptools.randomfunc()

            setuptools.setup(
                name = "hello",
                other = 23,
                example = ["item", "other"],
                python_requires = "1.24",
            )
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files._setup_py_python_requires() == "1.24"
    assert project_files.get_requires_python_str() == "1.24"


def test_read_setup_py_assign(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(dedent("""
            from setuptools import setup

            REQUIRES = "3.21"

            setuptools.setup(
                name = "hello",
                other = 23,
                example = ["item", "other"],
                python_requires = REQUIRES,
            )
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files._setup_py_python_requires() == "3.21"
    assert project_files.get_requires_python_str() == "3.21"


def test_read_setup_py_None(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(dedent("""
            from setuptools import setup

            REQUIRES = None

            setuptools.setup(
                name = "hello",
                other = 23,
                example = ["item", "other"],
                python_requires = None,
            )
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files._setup_py_python_requires() is None
    assert project_files.get_requires_python_str() is None


def test_read_setup_py_empty(tmp_path):
    with open(tmp_path / "setup.py", "w") as f:
        f.write(dedent("""
            from setuptools import setup

            REQUIRES = "3.21"

            setuptools.setup(
                name = "hello",
                other = 23,
                example = ["item", "other"],
            )
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files._setup_py_python_requires() is None
    assert project_files.get_requires_python_str() is None


def test_read_setup_cfg(tmp_path):
    with open(tmp_path / "setup.cfg", "w") as f:
        f.write(dedent("""
            [options]
            python_requires = 1.234
            [metadata]
            something = other
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files.setup_cfg["metadata"]["something"] == "other"
    assert dig(project_files.setup_cfg, "metadata", "something") == "other"
    assert dig(project_files.setup_cfg, "other", "something") is None
    assert project_files.get_requires_python_str() == "1.234"


def test_read_setup_cfg_empty(tmp_path):
    with open(tmp_path / "setup.cfg", "w") as f:
        f.write(dedent("""
            [options]
            other = 1.234
            [metadata]
            something = other
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files.get_requires_python_str() is None


def test_read_pyproject_toml(tmp_path):
    with open(tmp_path / "pyproject.toml", "w") as f:
        f.write(dedent("""
            [project]
            requires-python = "1.654"

            [tool.cibuildwheel]
            something = "other"
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files.pyproject_toml["tool"]["cibuildwheel"]["something"] == "other"
    assert dig(project_files.pyproject_toml, "tool", "cibuildwheel", "something") == "other"
    assert dig(project_files.pyproject_toml, "tool", "something", "other") is None
    assert project_files.get_requires_python_str() == "1.654"


def test_read_pyproject_toml_empty(tmp_path):
    with open(tmp_path / "pyproject.toml", "w") as f:
        f.write(dedent("""
            [project]
            other = 1.234
            """))

    project_files = ProjectFiles(tmp_path)
    assert project_files.exists()
    assert project_files.get_requires_python_str() is None
