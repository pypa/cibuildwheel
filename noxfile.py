from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import nox

nox.options.sessions = ["lint", "pylint", "check_manifest", "tests"]

PYTHON_ALL_VERSIONS = ["3.6", "3.7", "3.8", "3.9", "3.10", "3.11"]

DIR = Path(__file__).parent.resolve()

if os.environ.get("CI", None):
    nox.options.error_on_missing_interpreters = True


@nox.session
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    unit_test_args = ["--run-docker"] if sys.platform.startswith("linux") else []
    session.install("-e", ".[test]")
    if session.posargs:
        session.run("pytest", *session.posargs)
    else:
        session.run("pytest", "unit_test", *unit_test_args)
        session.run("pytest", "test", "-x", "--durations", "0", "--timeout=2400", "test")


@nox.session
def lint(session: nox.Session) -> None:
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session
def pylint(session: nox.Session) -> None:
    """
    Run pylint.
    """

    session.install("pylint", ".")
    session.run("pylint", "cibuildwheel", *session.posargs)


@nox.session
def check_manifest(session: nox.Session) -> None:
    """
    Ensure all needed files are included in the manifest.
    """

    session.install("check-manifest")
    session.run("check-manifest", *session.posargs)


@nox.session(python=PYTHON_ALL_VERSIONS)
def update_constraints(session: nox.Session) -> None:
    """
    Update the dependencies inplace.
    """
    session.install("pip-tools")
    assert isinstance(session.python, str)
    python_version = session.python.replace(".", "")
    env = os.environ.copy()
    # CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
    # regenerate the constraints files
    env["CUSTOM_COMPILE_COMMAND"] = f"nox -s {session.name}"
    session.run(
        "pip-compile",
        "--allow-unsafe",
        "--upgrade",
        "cibuildwheel/resources/constraints.in",
        f"--output-file=cibuildwheel/resources/constraints-python{python_version}.txt",
        env=env,
    )
    if session.python == PYTHON_ALL_VERSIONS[-1]:
        RESOURCES = DIR / "cibuildwheel" / "resources"
        shutil.copyfile(
            RESOURCES / f"constraints-python{python_version}.txt",
            RESOURCES / "constraints.txt",
        )


@nox.session
def update_pins(session: nox.Session) -> None:
    """
    Update the python, docker and virtualenv pins version inplace.
    """
    session.install("-e", ".[bin]")
    session.run("python", "bin/update_pythons.py", "--force")
    session.run("python", "bin/update_docker.py")
    session.run("python", "bin/update_virtualenv.py", "--force")


@nox.session
def update_proj(session: nox.Session) -> None:
    """
    Update the README inplace.
    """
    session.install("-e", ".[bin]")
    session.run(
        "python",
        "bin/projects.py",
        "docs/data/projects.yml",
        *session.posargs,
    )


@nox.session(python="3.9")
def docs(session: nox.Session) -> None:
    """
    Build the docs.
    """
    session.install("-e", ".[docs]")
    session.run("pip", "list")

    if session.posargs:
        if "serve" in session.posargs:
            session.run("mkdocs", "serve")
        else:
            session.error("Unrecognized args, use 'serve'")
    else:
        session.run("mkdocs", "build")


@nox.session
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
