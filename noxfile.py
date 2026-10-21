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

import dataclasses
import os
import re
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
    session.install("prek")
    session.run("prek", "run", "--all-files", *session.posargs)


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
        session.run("pytest", "cibuildwheel")  # run doctests
        session.run("pytest", "unit_test", *unit_test_args)
        session.run("pytest", "test", "-x", "--durations", "0", "--timeout=2400", "test")


@dataclasses.dataclass(frozen=True)
class HeldBackPin:
    package: str
    held: tuple[str, ...]
    graalpy_markers: tuple[str, ...]
    other_marker: str


# Packages held back for GraalPy 25.0 (Python 3.12). uv pip compile can't
# express a per-implementation split, so the compiled pin is patched: GraalPy
# (matching `graalpy_markers`) gets `held`, everything else (`other_marker`)
# tracks the freshly compiled version. These workarounds are fixed in GraalPy
# 25.3 (Python 3.13).
GRAALPY_25_0_HELD_BACK = (
    # Newer pip breaks GraalPy on macOS and Windows.
    HeldBackPin(
        package="pip",
        held=("26.1.2", "26.0.1"),
        graalpy_markers=(
            'implementation_name == "graalpy" and platform_system != "Windows"',
            'implementation_name == "graalpy" and platform_system == "Windows"',
        ),
        other_marker='implementation_name != "graalpy"',
    ),
    # filelock >=3.30 imports errno.ENOTSUP, which GraalPy lacks (fix due ~2026-08).
    HeldBackPin(
        package="filelock",
        held=("3.29.7",),
        graalpy_markers=('implementation_name == "graalpy"',),
        other_marker='implementation_name != "graalpy"',
    ),
)

# The constraints files are compiled for the host running the session, but pip's
# hash-checking mode refuses to install a package that isn't pinned in the file
# These are the platforms whose dependency closure each file has to cover
CONSTRAINTS_PLATFORMS = ("linux", "macos", "windows")
PYODIDE_CONSTRAINTS_PLATFORMS = ("linux", "macos")

# A pinned package followed by its block of `--hash` lines as written by pip/uv
HASHED_PIN_RE = r"^{package}==(?P<version>[^\s;\\]+) \\\n(?P<hashes>(?:[ ]+--hash=\S+(?: \\)?\n)+)"


def _pinned_names(constraints_text: str) -> set[str]:
    return {
        match[1].lower().replace("_", "-")
        for match in re.finditer(
            r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", constraints_text, flags=re.MULTILINE
        )
    }


def _check_platform_coverage(
    session: nox.Session,
    in_file: Path,
    output_file: Path,
    python_version: str,
    platforms: tuple[str, ...],
    env: dict[str, str],
) -> None:
    """
    Fail if a package needed on one of `platforms` is missing from `output_file`.
    """
    pinned = _pinned_names(output_file.read_text())
    for platform in platforms:
        platform_output = Path(session.create_tmp()) / f"{output_file.stem}-{platform}.txt"
        session.run(
            "uv",
            "pip",
            "compile",
            f"--python-version={python_version}",
            f"--python-platform={platform}",
            "--no-header",
            "--no-annotate",
            "--quiet",
            in_file,
            f"--output-file={platform_output}",
            env=env,
            silent=True,
        )
        missing = sorted(_pinned_names(platform_output.read_text()) - pinned)
        if missing:
            session.error(
                f"{output_file.name} doesn't pin {', '.join(missing)}, which {platform} needs. "
                f"Add them to {in_file.name}."
            )


def _hashed_pin(
    session: nox.Session,
    package: str,
    version: str,
    marker: str,
    python_version: str,
    env: dict[str, str],
) -> str:
    """
    Return `package==version; marker`, followed by its hashes.
    """
    in_file = Path(session.create_tmp()) / f"{package}-{version}.in"
    in_file.write_text(f"{package}=={version}\n")
    output = session.run(
        "uv",
        "pip",
        "compile",
        f"--python-version={python_version}",
        "--generate-hashes",
        "--no-deps",
        "--no-header",
        "--no-annotate",
        "--quiet",
        in_file,
        env=env,
        silent=True,
    )
    assert isinstance(output, str)
    hashes = re.findall(r"--hash=\S+", output)
    if not hashes:
        session.error(f"uv returned no hashes for {package}=={version}")
    lines = [f"{package}=={version}; {marker}", *(f"    {hash_}" for hash_ in hashes)]
    return " \\\n".join(lines) + "\n"


def _pin_graalpy_25_0_workarounds(
    session: nox.Session, output_file: Path, python_version: str, env: dict[str, str]
) -> None:
    text = output_file.read_text()
    for pin in GRAALPY_25_0_HELD_BACK:
        match = re.search(
            HASHED_PIN_RE.format(package=re.escape(pin.package)), text, flags=re.MULTILINE
        )
        if match is None:
            session.error(f"{pin.package} not found in {output_file}")
        replacement = f"{pin.package}=={match['version']}; {pin.other_marker} \\\n{match['hashes']}"
        for held, marker in zip(pin.held, pin.graalpy_markers, strict=True):
            replacement += _hashed_pin(session, pin.package, held, marker, python_version, env)
        text = text[: match.start()] + replacement + text[match.end() :]
    output_file.write_text(text)


@nox.session(default=False, tags=["update"])
def update_constraints(session: nox.Session) -> None:
    """
    Update the dependencies inplace. Pass `--no-upgrade` to keep the pinned
    versions and only regenerate the files.
    """

    resources = Path("cibuildwheel/resources")

    if session.venv_backend != "uv":
        session.install("uv>=0.9")

    # CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
    # regenerate the constraints files
    env = os.environ.copy()
    env["UV_CUSTOM_COMPILE_COMMAND"] = f"nox -s {session.name}"

    upgrade = [] if "--no-upgrade" in session.posargs else ["--upgrade"]
    build_platforms = nox.project.load_toml(resources / "build-platforms.toml")

    in_file = resources / "constraints.in"
    for minor_version in range(9, 16):
        python_version = f"3.{minor_version}"
        output_file = resources / f"constraints-python{python_version.replace('.', '')}.txt"
        session.run(
            "uv",
            "pip",
            "compile",
            f"--python-version={python_version}",
            "--generate-hashes",
            *upgrade,
            in_file,
            f"--output-file={output_file}",
            env=env,
        )
        _check_platform_coverage(
            session, in_file, output_file, python_version, CONSTRAINTS_PLATFORMS, env
        )
        if python_version == "3.12":
            _pin_graalpy_25_0_workarounds(session, output_file, python_version, env)

    shutil.copyfile(
        resources / "constraints-python315.txt",
        resources / "constraints.txt",
    )

    pyodides = build_platforms["pyodide"]["python_configurations"]
    for pyodide in pyodides:
        python_version = ".".join(pyodide["version"].split(".")[:2])
        pyodide_version = pyodide["default_pyodide_version"]

        tmp_file = Path(session.create_tmp()) / "constraints-pyodide.in"

        session.install_and_run_script(
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
            "--generate-hashes",
            *upgrade,
            tmp_file,
            f"--output-file={output_file}",
            env=env,
        )
        _check_platform_coverage(
            session, tmp_file, output_file, python_version, PYODIDE_CONSTRAINTS_PLATFORMS, env
        )


@nox.session(default=False, tags=["update"])
def update_pins(session: nox.Session) -> None:
    """
    Update the python, docker, virtualenv, node, and python-build-standalone
    version pins inplace.
    """
    session.install_and_run_script("bin/update_pythons.py", "--force")
    session.install_and_run_script("bin/update_docker.py")
    session.install_and_run_script("bin/update_virtualenv.py", "--force")
    session.install_and_run_script("bin/update_nodejs.py", "--force")
    session.install_and_run_script("bin/update_python_build_standalone.py")


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
    session.run(
        "properdocs", "serve" if session.interactive else "build", "--strict", *session.posargs
    )


@nox.session(default=False)
def update_how_it_works_image(session: nox.Session) -> None:
    """
    Generate the how it works image.
    """
    session.install_and_run_script("bin/update_how_it_works_image.py")


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
