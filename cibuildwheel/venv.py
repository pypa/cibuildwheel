from __future__ import annotations

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

from .typing import PathOrStr
from .util import resources
from .util.cmd import call
from .util.file import CIBW_CACHE_PATH, download

_IS_WIN: Final[bool] = sys.platform.startswith("win")


@functools.cache
def _ensure_virtualenv(version: str) -> Path:
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
    return path


def _parse_constraints_for_virtualenv(
    seed_packages: list[str],
    dependency_constraint_flags: Sequence[PathOrStr],
) -> dict[str, str]:
    """
    Parses the constraints file referenced by `dependency_constraint_flags` and returns a dict where
    the key is the package name, and the value is the constraint version.
    If a package version cannot be found, its value is "embed" meaning that virtualenv will install
    its bundled version, already available locally.
    The function does not try to be too smart and just handles basic constraints.
    If it can't get an exact version, the real constraint will be handled by the
    {macos|windows}.setup_python function.
    """
    assert len(dependency_constraint_flags) in {0, 2}
    # only seed pip if other seed packages do not appear in a constraint file
    constraints_dict = {"pip": "embed"}
    if len(dependency_constraint_flags) == 2:
        assert dependency_constraint_flags[0] == "-c"
        constraint_path = Path(dependency_constraint_flags[1])
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
                        package not in seed_packages
                        or requirement.url is not None
                        or requirement.marker is not None
                        or len(requirement.extras) != 0
                        or len(requirement.specifier) != 1
                    ):
                        continue
                    specifier = next(iter(requirement.specifier))
                    if specifier.operator != "==":
                        continue
                    constraints_dict[package] = specifier.version
                except InvalidRequirement:
                    continue
    return constraints_dict


def virtualenv(
    version: str,
    python: Path,
    venv_path: Path,
    dependency_constraint_flags: Sequence[PathOrStr],
    *,
    use_uv: bool,
) -> dict[str, str]:
    """
    Create a virtual environment. If `use_uv` is True,
    dependency_constraint_flags are ignored since nothing is installed in the
    venv. Otherwise, pip is installed, and setuptools + wheel if Python < 3.12.
    """
    assert python.exists()

    if use_uv:
        call("uv", "venv", venv_path, "--python", python)
    else:
        virtualenv_app = _ensure_virtualenv(version)
        allowed_seed_packages = ["pip", "setuptools", "wheel"]
        constraints = _parse_constraints_for_virtualenv(
            allowed_seed_packages, dependency_constraint_flags
        )
        additional_flags: list[str] = []
        for package in allowed_seed_packages:
            if package in constraints:
                additional_flags.append(f"--{package}={constraints[package]}")
            else:
                additional_flags.append(f"--no-{package}")

        # Using symlinks to pre-installed seed packages is really the fastest way to get a virtual
        # environment. The initial cost is a bit higher but reusing is much faster.
        # Windows does not always allow symlinks so just disabling for now.
        # Requires pip>=19.3 so disabling for "embed" because this means we don't know what's the
        # version of pip that will end-up installed.
        # c.f. https://virtualenv.pypa.io/en/latest/cli_interface.html#section-seeder
        if (
            not _IS_WIN
            and constraints["pip"] != "embed"
            and Version(constraints["pip"]) >= Version("19.3")
        ):
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
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([*paths, env["PATH"]])
    env["VIRTUAL_ENV"] = str(venv_path)
    return env


def find_uv() -> Path | None:
    # Prefer uv in our environment
    with contextlib.suppress(ImportError, FileNotFoundError):
        # pylint: disable-next=import-outside-toplevel
        from uv import find_uv_bin

        return Path(find_uv_bin())

    uv_on_path = shutil.which("uv")
    return Path(uv_on_path) if uv_on_path else None
