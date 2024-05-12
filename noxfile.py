from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import nox

nox.options.sessions = ["lint", "pylint", "check_manifest", "tests"]

DIR = Path(__file__).parent.resolve()

if os.environ.get("CI", None):
    nox.options.error_on_missing_interpreters = True


@nox.session
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    unit_test_args = ["--run-docker"] if sys.platform.startswith("linux") else []
    session.install("-e.[test]")
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

    name = "cibuildwheel @ ." if getattr(session.virtualenv, "venv_backend", "") == "uv" else "."
    session.install("pylint", name)
    session.run("pylint", "cibuildwheel", *session.posargs)


@nox.session
def check_manifest(session: nox.Session) -> None:
    """
    Ensure all needed files are included in the manifest.
    """

    session.install("check-manifest")
    session.run("check-manifest", *session.posargs)


@nox.session
def update_constraints(session: nox.Session) -> None:
    """
    Update the dependencies inplace.
    """

    if getattr(session.virtualenv, "venv_backend", "") != "uv":
        session.install("uv>=0.1.23")

    for minor_version in range(7, 14):
        python_version = f"3.{minor_version}"
        env = os.environ.copy()
        # CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
        # regenerate the constraints files
        env["UV_CUSTOM_COMPILE_COMMAND"] = f"nox -s {session.name}"
        session.run(
            "uv",
            "pip",
            "compile",
            f"--python-version={python_version}",
            "--upgrade",
            "cibuildwheel/resources/constraints.in",
            f"--output-file=cibuildwheel/resources/constraints-python{python_version.replace('.', '')}.txt",
            env=env,
        )
    RESOURCES = DIR / "cibuildwheel" / "resources"
    shutil.copyfile(
        RESOURCES / "constraints-python312.txt",
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
    session.install("-e.[bin]")
    session.run(
        "python",
        "bin/projects.py",
        "docs/data/projects.yml",
        *session.posargs,
    )


@nox.session(reuse_venv=True)
def generate_schema(session: nox.Session) -> None:
    """
    Generate the cibuildwheel.schema.json file.
    """
    session.install("pyyaml")
    output = session.run("python", "bin/generate_schema.py", silent=True)
    assert isinstance(output, str)
    DIR.joinpath("cibuildwheel/resources/cibuildwheel.schema.json").write_text(output)


@nox.session(python="3.9")
def docs(session: nox.Session) -> None:
    """
    Build the docs. Will serve unless --non-interactive
    """
    session.install("-e.[docs]")
    session.run("mkdocs", "serve" if session.interactive else "build", "--strict", *session.posargs)


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
