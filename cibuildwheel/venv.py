from __future__ import annotations

__lazy_modules__ = {
    "cibuildwheel.util",
    "cibuildwheel.util.cmd",
    "cibuildwheel.util.file",
    "contextlib",
    "filelock",
    "packaging",
    "packaging.markers",
    "packaging.requirements",
    "packaging.version",
    "pathlib",
    "shutil",
    "tomllib",
}

import contextlib
import functools
import os
import shutil
import sys
import tomllib
from pathlib import Path
from typing import cast

from filelock import FileLock
from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

from cibuildwheel.util import resources
from cibuildwheel.util.cmd import call
from cibuildwheel.util.file import CIBW_CACHE_PATH, download, remove_on_error

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final

_IS_WIN: Final[bool] = sys.platform.startswith("win")


def target_marker_env(
    *,
    implementation_id: str,
) -> dict[str, str]:
    """
    Build a PEP 508 marker environment dict for the target Python,
    overriding the host's values with the target implementation info.
    """
    env = cast("dict[str, str]", default_environment())
    if implementation_id.startswith("gp"):
        env["implementation_name"] = "graalpy"
        env["platform_python_implementation"] = "GraalPy"
    elif implementation_id.startswith("pp"):
        env["implementation_name"] = "pypy"
        env["platform_python_implementation"] = "PyPy"
    return env


@functools.cache
def _ensure_virtualenv(version: str) -> tuple[Path, Version]:
    version_parts = version.split(".")
    key = f"py{version_parts[0]}{version_parts[1]}"
    with resources.VIRTUALENV.open("rb") as f:
        loaded_file = tomllib.load(f)
    configuration = loaded_file.get(key, loaded_file["default"])
    version = str(configuration["version"])
    url = str(configuration["url"])
    sha256 = str(configuration["sha256"])
    path = CIBW_CACHE_PATH / f"virtualenv-{version}.pyz"
    with FileLock(str(path) + ".lock"):
        if not path.exists():
            with remove_on_error(path):
                download(url, path, sha256=sha256)
    return (path, Version(version))


def constraint_flags(
    dependency_constraint: Path | None,
) -> Sequence[str]:
    """
    Returns the flags to pass to pip for the given dependency constraint.
    """

    return ["-c", dependency_constraint.as_uri()] if dependency_constraint else []


def _parse_pip_constraint_for_virtualenv(
    constraint_path: Path | None,
    marker_env: dict[str, str] | None = None,
) -> str:
    """
    Parses the constraints file referenced by `dependency_constraint_flags` and returns a dict where
    the key is the package name, and the value is the constraint version.
    If a package version cannot be found, its value is "embed" meaning that virtualenv will install
    its bundled version, already available locally.
    The function does not try to be too smart and just handles basic constraints.
    If it can't get an exact version, the real constraint will be handled by the
    {macos|windows}.setup_python function.
    If marker_env is provided, marker-bearing constraints are evaluated against it;
    otherwise, they are evaluated against the host's default environment.
    """
    env: dict[str, str] = (
        marker_env if marker_env is not None else cast("dict[str, str]", default_environment())
    )
    if constraint_path:
        assert constraint_path.exists()
        with constraint_path.open(encoding="utf-8") as constraint_file:
            for line_ in constraint_file:
                line = line_.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                try:
                    requirement = Requirement(line)
                    package = requirement.name
                    if (
                        package != "pip"
                        or requirement.url is not None
                        or len(requirement.extras) != 0
                        or len(requirement.specifier) != 1
                    ):
                        continue
                    if requirement.marker is not None and not requirement.marker.evaluate(env):
                        continue
                    specifier = next(iter(requirement.specifier))
                    if specifier.operator != "==":
                        continue
                    return specifier.version
                except InvalidRequirement:
                    continue
    return "embed"


def virtualenv(
    version: str,
    python: Path,
    venv_path: Path,
    dependency_constraint: Path | None,
    *,
    use_uv: bool,
    env: dict[str, str] | None = None,
    pip_version: str | None = None,
    marker_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Create a virtual environment. If `use_uv` is True,
    dependency_constraint_flags are ignored since nothing is installed in the
    venv. Otherwise, pip is installed.
    """

    # virtualenv may fail if this is a symlink.
    python = python.resolve()

    assert python.exists()

    if use_uv:
        uv_path = find_uv()
        assert uv_path is not None
        call(uv_path, "venv", venv_path, "--python", python)
    else:
        virtualenv_app, virtualenv_version = _ensure_virtualenv(version)
        if pip_version is None:
            pip_version = _parse_pip_constraint_for_virtualenv(dependency_constraint, marker_env)
        additional_flags = [f"--pip={pip_version}", "--no-setuptools"]
        if virtualenv_version < Version("20.31") or Version(version) < Version("3.9"):
            additional_flags.append("--no-wheel")

        # Using symlinks to pre-installed seed packages is really the fastest way to get a virtual
        # environment. The initial cost is a bit higher but reusing is much faster.
        # Windows does not always allow symlinks so just disabling for now.
        # Requires pip>=19.3 so disabling for "embed" because this means we don't know what's the
        # version of pip that will end-up installed.
        # c.f. https://virtualenv.pypa.io/en/latest/cli_interface.html#section-seeder
        if not _IS_WIN and pip_version != "embed" and Version(pip_version) >= Version("19.3"):
            additional_flags.append("--symlink-app-data")

        call(
            sys.executable,
            "-sS",  # just the stdlib, https://github.com/pypa/virtualenv/issues/2133#issuecomment-1003710125
            virtualenv_app,
            "--activators=",
            "--no-periodic-update",
            *additional_flags,
            "--python",
            python,
            venv_path,
        )
    if not _IS_WIN:
        _symlink_python_config_scripts(python, venv_path / "bin")
    venv_env = activate_virtualenv(venv_path, env=env)
    if not use_uv and pip_version == "embed":
        call(
            "python",
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            *constraint_flags(dependency_constraint),
            env=venv_env,
            cwd=venv_path,
        )
    return venv_env


def _symlink_python_config_scripts(base_python: Path, venv_bin: Path) -> None:
    """
    Symlink the base interpreter's ``python*-config`` scripts into the venv's
    bin directory if provided and not already linked (virtualenvs don't always
    provide them).
    """
    # The config scripts live next to the base interpreter, e.g.
    # `python3-config` and `python3.12-config`.
    for config_script in sorted(base_python.parent.glob("python*-config")):
        target = venv_bin / config_script.name
        if target.exists() or target.is_symlink():
            continue
        with contextlib.suppress(OSError):
            target.symlink_to(config_script)


def activate_virtualenv(
    venv_path: Path,
    env: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Return a copy of the environment with the virtualenv at `venv_path` activated.
    """
    paths = [str(venv_path), str(venv_path / "Scripts")] if _IS_WIN else [str(venv_path / "bin")]
    venv_env = os.environ.copy() if env is None else env.copy()
    venv_env["PATH"] = os.pathsep.join([*paths, venv_env["PATH"]])
    venv_env["VIRTUAL_ENV"] = str(venv_path)
    return venv_env


def find_uv() -> Path | None:
    # Prefer uv in our environment
    with contextlib.suppress(ImportError, FileNotFoundError):
        from uv import find_uv_bin  # noqa: PLC0415

        return Path(find_uv_bin())

    uv_on_path = shutil.which("uv")
    return Path(uv_on_path) if uv_on_path else None
