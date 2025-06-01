#!/usr/bin/env -S uv run

# /// script
# dependencies = ["nox>=2025.2.9"]
# ///

"""
cibuildwheel's nox support

Tags:

    lint: All linting jobs
    update: All update jobs

See sessions with `nox -l`
"""

import os
import shutil
import sys
from pathlib import Path

import nox

nox.needs_version = ">=2025.2.9"
nox.options.default_venv_backend = "uv|virtualenv"

DIR = Path(__file__).parent.resolve()


@nox.session(tags=["lint"])
def lint(session: nox.Session) -> None:
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(tags=["lint"])
def pylint(session: nox.Session) -> None:
    """
    Run pylint.
    """

    session.install("pylint>=3.2", "-e.")
    session.run("pylint", "cibuildwheel", *session.posargs)


@nox.session
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    pyproject = nox.project.load_toml()
    session.install("-e.", *nox.project.dependency_groups(pyproject, "test"))
    if session.posargs:
        session.run("pytest", *session.posargs)
    else:
        unit_test_args = ["--run-docker"] if sys.platform.startswith("linux") else []
        session.run("pytest", "unit_test", *unit_test_args)
        session.run("pytest", "test", "-x", "--durations", "0", "--timeout=2400", "test")


@nox.session(default=False, tags=["update"])
def update_constraints(session: nox.Session) -> None:
    """
    Update the dependencies inplace.
    """

    session.install("-e.", "click")

    resources = Path("cibuildwheel/resources")

    if session.venv_backend != "uv":
        session.install("uv>=0.1.23")

    # CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
    # regenerate the constraints files
    env = os.environ.copy()
    env["UV_CUSTOM_COMPILE_COMMAND"] = f"nox -s {session.name}"

    for minor_version in range(8, 15):
        python_version = f"3.{minor_version}"
        output_file = resources / f"constraints-python{python_version.replace('.', '')}.txt"
        session.run(
            "uv",
            "pip",
            "compile",
            f"--python-version={python_version}",
            "--upgrade",
            resources / "constraints.in",
            f"--output-file={output_file}",
            env=env,
        )

    shutil.copyfile(
        resources / "constraints-python314.txt",
        resources / "constraints.txt",
    )

    build_platforms = nox.project.load_toml(resources / "build-platforms.toml")
    pyodides = build_platforms["pyodide"]["python_configurations"]
    for pyodide in pyodides:
        python_version = ".".join(pyodide["version"].split(".")[:2])
        pyodide_version = pyodide["default_pyodide_version"]

        tmp_file = Path(session.create_tmp()) / "constraints-pyodide.in"

        session.run(
            "python",
            "bin/generate_pyodide_constraints.py",
            "--output-file",
            tmp_file,
            pyodide_version,
        )

        output_file = resources / f"constraints-pyodide{python_version.replace('.', '')}.txt"
        session.run(
            "uv",
            "pip",
            "compile",
            f"--python-version={python_version}",
            "--upgrade",
            tmp_file,
            f"--output-file={output_file}",
            env=env,
        )


@nox.session(default=False, tags=["update"])
def update_pins(session: nox.Session) -> None:
    """
    Update the python, docker, virtualenv, node, and python-build-standalone
    version pins inplace.
    """
    pyproject = nox.project.load_toml()
    session.install("-e.", *nox.project.dependency_groups(pyproject, "bin"))
    session.run("python", "bin/update_pythons.py", "--force")
    session.run("python", "bin/update_docker.py")
    session.run("python", "bin/update_virtualenv.py", "--force")
    session.run("python", "bin/update_nodejs.py", "--force")
    session.run("python", "bin/update_python_build_standalone.py")


@nox.session(default=False, reuse_venv=True, tags=["update"])
def update_proj(session: nox.Session) -> None:
    """
    Update the README inplace.
    """
    session.install_and_run_script(
        "bin/projects.py",
        "docs/data/projects.yml",
        *session.posargs,
    )


@nox.session(default=False, reuse_venv=True, tags=["update"])
def generate_schema(session: nox.Session) -> None:
    """
    Generate the cibuildwheel.schema.json file.
    """
    output = session.install_and_run_script("bin/generate_schema.py", silent=True)
    assert isinstance(output, str)
    DIR.joinpath("cibuildwheel/resources/cibuildwheel.schema.json").write_text(output)


@nox.session(default=False, reuse_venv=True)
def bump_version(session: nox.Session) -> None:
    """
    Bump cibuildwheel's version. Interactive.
    """
    session.install_and_run_script("bin/bump_version.py")


@nox.session(default=False)
def docs(session: nox.Session) -> None:
    """
    Build the docs. Will serve unless --non-interactive
    """
    pyproject = nox.project.load_toml()
    session.install("-e.", *nox.project.dependency_groups(pyproject, "docs"))
    session.run("mkdocs", "serve" if session.interactive else "build", "--strict", *session.posargs)


@nox.session(default=False)
def build(session: nox.Session) -> None:
    """
    Build an SDist and wheel.
    """

    build_p = DIR.joinpath("build")
    if build_p.exists():
        shutil.rmtree(build_p)

    dist_p = DIR.joinpath("dist")
    if dist_p.exists():
        shutil.rmtree(dist_p)

    session.install("build")
    session.run("python", "-m", "build")


if __name__ == "__main__":
    nox.main()
