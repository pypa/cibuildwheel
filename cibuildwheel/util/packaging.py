from __future__ import annotations

import shlex
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, Literal, TypeVar

from packaging.utils import parse_wheel_filename

from . import resources
from .cmd import call
from .helpers import parse_key_value_string, unwrap


@dataclass()
class DependencyConstraints:
    base_file_path: Path | None = None
    packages: list[str] | None = None

    def __post_init__(self) -> None:
        if self.packages is not None and self.base_file_path is not None:
            msg = "Cannot specify both a file and packages in the dependency constraints"
            raise ValueError(msg)

        if self.base_file_path is not None:
            assert self.base_file_path.exists()
            self.base_file_path = self.base_file_path.resolve()

    @staticmethod
    def with_defaults() -> DependencyConstraints:
        return DependencyConstraints(base_file_path=resources.CONSTRAINTS)

    @staticmethod
    def from_config_string(config_string: str) -> DependencyConstraints | None:
        if config_string == "pinned":
            return DependencyConstraints.with_defaults()

        if config_string == "latest":
            return None

        if config_string.startswith(("file:", "packages:")):
            return DependencyConstraints.from_table_style_config_string(config_string)

        return DependencyConstraints(base_file_path=Path(config_string))

    @staticmethod
    def from_table_style_config_string(config_string: str) -> DependencyConstraints | None:
        config_dict = parse_key_value_string(config_string, ["file"], ["packages"])
        files = config_dict.get("file")
        packages = config_dict.get("packages")

        if files and packages:
            msg = "Cannot specify both a file and packages in dependency-versions"
            raise ValueError(msg)

        if packages:
            return DependencyConstraints(packages=packages)

        if not files:
            return DependencyConstraints.with_defaults()

        if len(files) > 1:
            msg = unwrap("""
                Only one file can be specified in dependency-versions.
                If you intended to pass only one, perhaps you need to quote the path?
            """)
            raise ValueError(msg)

        return DependencyConstraints(base_file_path=Path(files[0]))

    def get_for_python_version(
        self, *, version: str, variant: Literal["python", "pyodide"] = "python", tmp_dir: Path
    ) -> Path:
        if self.packages:
            constraint_file = tmp_dir / "constraints.txt"
            constraint_file.write_text("\n".join(self.packages))
            return constraint_file

        assert self.base_file_path is not None, (
            "DependencyConstraints should have either a file or packages"
        )

        version_parts = version.split(".")

        # try to find a version-specific dependency file e.g. if
        # ./constraints.txt is the base, look for ./constraints-python36.txt
        specific_stem = self.base_file_path.stem + f"-{variant}{version_parts[0]}{version_parts[1]}"
        specific_name = specific_stem + self.base_file_path.suffix
        specific_file_path = self.base_file_path.with_name(specific_name)

        if specific_file_path.exists():
            return specific_file_path
        else:
            return self.base_file_path

    def options_summary(self) -> Any:
        if self == DependencyConstraints.with_defaults():
            return "pinned"
        elif self.packages:
            return {"packages": " ".join(shlex.quote(p) for p in self.packages)}
        else:
            assert self.base_file_path is not None, (
                "DependencyConstraints should have either a file or packages"
            )
            return self.base_file_path.name


def get_pip_version(env: Mapping[str, str]) -> str:
    versions_output_text = call(
        "python", "-m", "pip", "freeze", "--all", capture_stdout=True, env=env
    )
    (pip_version,) = (
        version[5:]
        for version in versions_output_text.strip().splitlines()
        if version.startswith("pip==")
    )
    return pip_version


T = TypeVar("T", bound=PurePath)


def find_compatible_wheel(wheels: Sequence[T], identifier: str) -> T | None:
    """
    Finds a wheel with an abi3 or a none ABI tag in `wheels` compatible with the Python interpreter
    specified by `identifier` that is previously built.
    """

    interpreter, platform = identifier.split("-")
    free_threaded = interpreter.endswith("t")
    if free_threaded:
        interpreter = interpreter[:-1]
    for wheel in wheels:
        _, _, _, tags = parse_wheel_filename(wheel.name)
        for tag in tags:
            if tag.abi == "abi3" and not free_threaded:
                # ABI3 wheels must start with cp3 for impl and tag
                if not (interpreter.startswith("cp3") and tag.interpreter.startswith("cp3")):
                    continue
            elif tag.abi == "none":
                # CPythonless wheels must include py3 tag
                if tag.interpreter[:3] != "py3":
                    continue
            else:
                # Other types of wheels are not detected, this is looking for previously built wheels.
                continue

            if tag.interpreter != "py3" and int(tag.interpreter[3:]) > int(interpreter[3:]):
                # If a minor version number is given, it has to be lower than the current one.
                continue

            if platform.startswith(("manylinux", "musllinux", "macosx")):
                # Linux, macOS require the beginning and ending match (macos/manylinux version doesn't need to)
                os_, arch = platform.split("_", 1)
                if not tag.platform.startswith(os_):
                    continue
                if not tag.platform.endswith(f"_{arch}"):
                    continue
            else:
                # Windows should exactly match
                if tag.platform != platform:
                    continue

            # If all the filters above pass, then the wheel is a previously built compatible wheel.
            return wheel

    return None


def combine_constraints(
    env: MutableMapping[str, str], /, constraints_path: Path, tmp_dir: Path | None
) -> None:
    """
    This will workaround a bug in pip<=21.1.1 or uv<=0.2.0 if a tmp_dir is given.
    If set to None, this will use the modern URI method.
    """

    if tmp_dir:
        if " " in str(constraints_path):
            assert " " not in str(tmp_dir)
            tmp_file = tmp_dir / "constraints.txt"
            tmp_file.write_bytes(constraints_path.read_bytes())
            constraints_path = tmp_file
        our_constraints = str(constraints_path)
    else:
        our_constraints = (
            constraints_path.as_uri() if " " in str(constraints_path) else str(constraints_path)
        )

    user_constraints = env.get("PIP_CONSTRAINT")

    env["UV_CONSTRAINT"] = env["PIP_CONSTRAINT"] = " ".join(
        c for c in [our_constraints, user_constraints] if c
    )
