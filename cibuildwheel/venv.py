import contextlib
import functools
import os
import shutil
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from filelock import FileLock
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

from .util import resources
from .util.cmd import call
from .util.file import CIBW_CACHE_PATH, download

_IS_WIN: Final[bool] = sys.platform.startswith("win")


@functools.cache
def _ensure_virtualenv(version: str) -> tuple[Path, Version]:
    version_parts = version.split(".")
    key = f"py{version_parts[0]}{version_parts[1]}"
    with resources.VIRTUALENV.open("rb") as f:
        loaded_file = tomllib.load(f)
    configuration = loaded_file.get(key, loaded_file["default"])
    version = str(configuration["version"])
    url = str(configuration["url"])
    path = CIBW_CACHE_PATH / f"virtualenv-{version}.pyz"
    with FileLock(str(path) + ".lock"):
        if not path.exists():
            download(url, path)
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
) -> str:
    """
    Parses the constraints file referenced by `dependency_constraint_flags` and returns a dict where
    the key is the package name, and the value is the constraint version.
    If a package version cannot be found, its value is "embed" meaning that virtualenv will install
    its bundled version, already available locally.
    The function does not try to be too smart and just handles basic constraints.
    If it can't get an exact version, the real constraint will be handled by the
    {macos|windows}.setup_python function.
    """
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
                        or requirement.marker is not None
                        or len(requirement.extras) != 0
                        or len(requirement.specifier) != 1
                    ):
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
        call("uv", "venv", venv_path, "--python", python)
    else:
        virtualenv_app, virtualenv_version = _ensure_virtualenv(version)
        if pip_version is None:
            pip_version = _parse_pip_constraint_for_virtualenv(dependency_constraint)
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
    paths = [str(venv_path), str(venv_path / "Scripts")] if _IS_WIN else [str(venv_path / "bin")]
    venv_env = os.environ.copy() if env is None else env.copy()
    venv_env["PATH"] = os.pathsep.join([*paths, venv_env["PATH"]])
    venv_env["VIRTUAL_ENV"] = str(venv_path)
    if not use_uv and pip_version == "embed":
        call(
            "pip",
            "install",
            "--upgrade",
            "pip",
            *constraint_flags(dependency_constraint),
            env=venv_env,
            cwd=venv_path,
        )
    return venv_env


def find_uv() -> Path | None:
    # Prefer uv in our environment
    with contextlib.suppress(ImportError, FileNotFoundError):
        # pylint: disable-next=import-outside-toplevel
        from uv import find_uv_bin

        return Path(find_uv_bin())

    uv_on_path = shutil.which("uv")
    return Path(uv_on_path) if uv_on_path else None
