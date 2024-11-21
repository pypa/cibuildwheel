from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

import nox

nox.needs_version = ">=2024.4.15"
nox.options.sessions = ["lint", "pylint", "check_manifest", "tests"]
nox.options.default_venv_backend = "uv|virtualenv"

DIR = Path(__file__).parent.resolve()


def install_and_run(session: nox.Session, script: str, *args: str, **kwargs: Any) -> str | None:
    deps = nox.project.load_toml(script)["dependencies"]
    session.install(*deps)
    return session.run("python", script, *args, **kwargs)


def dep_group(group: str) -> list[str]:
    return nox.project.load_toml("pyproject.toml")["dependency-groups"][group]  # type: ignore[no-any-return]


@nox.session
def tests(session: nox.Session) -> None:
    """
    Run the unit and regular tests.
    """
    session.install("-e.", *dep_group("test"))
    if session.posargs:
        session.run("pytest", *session.posargs)
    else:
        unit_test_args = ["--run-docker"] if sys.platform.startswith("linux") else []
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

    session.install("pylint>=3.2", "-e.")
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

    resources = Path("cibuildwheel/resources")

    if session.venv_backend != "uv":
        session.install("uv>=0.1.23")

    for minor_version in range(7, 14):
        python_version = f"3.{minor_version}"
        env = os.environ.copy()
        # CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
        # regenerate the constraints files
        env["UV_CUSTOM_COMPILE_COMMAND"] = f"nox -s {session.name}"
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
        resources / "constraints-python312.txt",
        resources / "constraints.txt",
    )

    build_platforms = nox.project.load_toml(resources / "build-platforms.toml")
    pyodides = build_platforms["pyodide"]["python_configurations"]
    for pyodide in pyodides:
        python_version = ".".join(pyodide["version"].split(".")[:2])
        pyodide_build_version = pyodide["pyodide_build_version"]
        output_file = resources / f"constraints-pyodide{python_version.replace('.', '')}.txt"
        tmp_file = Path(session.create_tmp()) / "constraints-pyodide.in"
        tmp_file.write_text(f"pip\nbuild[virtualenv]\npyodide-build=={pyodide_build_version}")
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


@nox.session
def update_pins(session: nox.Session) -> None:
    """
    Update the python, docker and virtualenv pins version inplace.
    """
    session.install("-e.", *dep_group("bin"))
    session.run("python", "bin/update_pythons.py", "--force")
    session.run("python", "bin/update_docker.py")
    session.run("python", "bin/update_virtualenv.py", "--force")
    session.run("python", "bin/update_nodejs.py", "--force")


@nox.session(reuse_venv=True)
def update_proj(session: nox.Session) -> None:
    """
    Update the README inplace.
    """
    install_and_run(
        session,
        "bin/projects.py",
        "docs/data/projects.yml",
        *session.posargs,
    )


@nox.session(reuse_venv=True)
def generate_schema(session: nox.Session) -> None:
    """
    Generate the cibuildwheel.schema.json file.
    """
    output = install_and_run(session, "bin/generate_schema.py", silent=True)
    assert isinstance(output, str)
    DIR.joinpath("cibuildwheel/resources/cibuildwheel.schema.json").write_text(output)


@nox.session(reuse_venv=True)
def bump_version(session: nox.Session) -> None:
    """
    Bump cibuildwheel's version. Interactive.
    """
    install_and_run(session, "bin/bump_version.py")


@nox.session(python="3.12")
def docs(session: nox.Session) -> None:
    """
    Build the docs. Will serve unless --non-interactive
    """
    session.install("-e.", *dep_group("docs"))
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
