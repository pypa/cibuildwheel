import shlex
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, Literal, Self, TypeVar

from packaging.utils import parse_wheel_filename

from . import resources
from .cmd import call
from .helpers import parse_key_value_string, unwrap


@dataclass(kw_only=True)
class DependencyConstraints:
    base_file_path: Path | None = None
    packages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.packages and self.base_file_path is not None:
            msg = "Cannot specify both a file and packages in the dependency constraints"
            raise ValueError(msg)

        if self.base_file_path is not None:
            if not self.base_file_path.exists():
                msg = f"Dependency constraints file not found: {self.base_file_path}"
                raise FileNotFoundError(msg)
            self.base_file_path = self.base_file_path.resolve()

    @classmethod
    def pinned(cls) -> Self:
        return cls(base_file_path=resources.CONSTRAINTS)

    @classmethod
    def latest(cls) -> Self:
        return cls()

    @classmethod
    def from_config_string(cls, config_string: str) -> Self:
        if config_string == "pinned":
            return cls.pinned()

        if config_string == "latest" or not config_string:
            return cls.latest()

        if config_string.startswith(("file:", "packages:")):
            # we only do the table-style parsing if it looks like a table,
            # because this option used to be only a file path. We don't want
            # to break existing configurations, whose file paths might include
            # special characters like ':' or ' ', which would require quoting
            # if they were to be passed as a parse_key_value_string positional
            # argument.
            return cls.from_table_style_config_string(config_string)

        return cls(base_file_path=Path(config_string))

    @classmethod
    def from_table_style_config_string(cls, config_string: str) -> Self:
        config_dict = parse_key_value_string(config_string, kw_arg_names=["file", "packages"])
        files = config_dict.get("file")
        packages = config_dict.get("packages") or []

        if files and packages:
            msg = "Cannot specify both a file and packages in dependency-versions"
            raise ValueError(msg)

        if files:
            if len(files) > 1:
                msg = unwrap("""
                    Only one file can be specified in dependency-versions.
                    If you intended to pass only one, perhaps you need to quote the path?
                """)
                raise ValueError(msg)

            return cls(base_file_path=Path(files[0]))

        return cls(packages=packages)

    def get_for_python_version(
        self, *, version: str, variant: Literal["python", "pyodide"] = "python", tmp_dir: Path
    ) -> Path | None:
        if self.packages:
            constraint_file = tmp_dir / "constraints.txt"
            constraint_file.write_text("\n".join(self.packages))
            return constraint_file

        if self.base_file_path is not None:
            version_parts = version.split(".")

            # try to find a version-specific dependency file e.g. if
            # ./constraints.txt is the base, look for ./constraints-python36.txt
            specific_stem = (
                self.base_file_path.stem + f"-{variant}{version_parts[0]}{version_parts[1]}"
            )
            specific_name = specific_stem + self.base_file_path.suffix
            specific_file_path = self.base_file_path.with_name(specific_name)

            if specific_file_path.exists():
                return specific_file_path
            else:
                return self.base_file_path

        return None

    def options_summary(self) -> Any:
        if self == DependencyConstraints.pinned():
            return "pinned"
        elif self.packages:
            return {"packages": " ".join(shlex.quote(p) for p in self.packages)}
        elif self.base_file_path is not None:
            return self.base_file_path.name
        else:
            return "latest"


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

    interpreter, platform = identifier.split("-", 1)
    interpreter = interpreter.split("_")[0]
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

            if platform.startswith(("manylinux", "musllinux", "macosx", "ios")):
                # Linux, macOS, and iOS require the beginning and ending match
                # (macos/manylinux/iOS version number doesn't need to match)
                os_, arch = platform.split("_", 1)
                if not tag.platform.startswith(os_):
                    continue
                if not tag.platform.endswith(f"_{arch}"):
                    continue
            elif platform.startswith("pyodide"):
                # each Pyodide version has its own platform tag
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
