from __future__ import annotations

__lazy_modules__ = {
    "cibuildwheel.util.cmd",
    "cibuildwheel.util.helpers",
    "packaging",
    "packaging.utils",
    "shlex",
    "zipfile",
}

import shlex
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import TypeVar
from zipfile import ZipFile

from packaging.utils import parse_wheel_filename

from cibuildwheel.util import resources
from cibuildwheel.util.cmd import call
from cibuildwheel.util.helpers import parse_key_value_string, unwrap

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Literal, Self


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

    def options_summary(self) -> str | dict[str, str]:
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

            if platform.startswith(("manylinux", "musllinux", "macosx", "android", "ios")):
                # On these platforms the wheel tag includes a platform version number, which we
                # should ignore.
                os_, arch = platform.split("_", 1)
                if not tag.platform.startswith(os_):
                    continue
                if not tag.platform.endswith(f"_{arch}"):
                    continue
            elif platform.startswith("pyodide"):
                # each Pyodide version has its own platform tag
                continue
            # Windows should exactly match
            elif tag.platform != platform:
                continue

            # If all the filters above pass, then the wheel is a previously built compatible wheel.
            return wheel

    return None


def is_abi3_wheel(wheel_name: str) -> bool:
    """Check if a wheel uses the abi3 stable ABI based on its filename."""
    _, _, _, tags = parse_wheel_filename(wheel_name)
    return any(tag.abi == "abi3" for tag in tags)


_IMPORTABLE_SUFFIXES = (".py", ".pyc", ".pyi", ".pyd", ".so")
_INIT_NAMES = {f"__init__{suffix}" for suffix in _IMPORTABLE_SUFFIXES}


def pep420_namespace_packages(wheel: Path) -> tuple[str, ...]:
    """Return dotted names of PEP 420 namespace packages in ``wheel``.

    A directory is a namespace package when it contains importable modules (or
    subpackages) but no ``__init__`` module. Nested namespaces collapse so that
    ``foo.bar`` covers both ``foo`` and ``foo.bar``, which is the form
    delvewheel wants for ``--namespace-pkg``.
    """
    with ZipFile(wheel) as zf:
        names = {name.replace("\\", "/") for name in zf.namelist()}

    package_dirs: set[str] = set()
    for name in names:
        if name.endswith("/"):
            continue
        parts = name.split("/")
        root = parts[0]
        if root.endswith((".dist-info", ".data")):
            continue
        if not parts[-1].endswith(_IMPORTABLE_SUFFIXES):
            continue
        for depth in range(1, len(parts)):
            package_dirs.add("/".join(parts[:depth]))

    namespaces: set[str] = set()
    for package_dir in package_dirs:
        if not any(f"{package_dir}/{init_name}" in names for init_name in _INIT_NAMES):
            namespaces.add(package_dir.replace("/", "."))

    collapsed: list[str] = []
    for name in sorted(namespaces, key=lambda item: item.count("."), reverse=True):
        if any(kept == name or kept.startswith(f"{name}.") for kept in collapsed):
            continue
        collapsed.append(name)
    return tuple(sorted(collapsed))


def with_delvewheel_namespace_pkgs(command: str, packages: Sequence[str]) -> str:
    """Add ``--namespace-pkg`` to a delvewheel repair command when needed.

    delvewheel's default strategy writes a top-level ``__init__.py`` so it can
    call ``os.add_dll_directory``. That turns a PEP 420 namespace package into
    a regular package. ``--namespace-pkg`` selects the alternate strategy.

    The delimiter is ``;`` because delvewheel only runs on Windows. Existing
    ``--namespace-pkg`` flags and non-delvewheel commands are left unchanged.
    """
    if not packages or "delvewheel" not in command or "--namespace-pkg" in command:
        return command
    return f'{command} --namespace-pkg "{";".join(packages)}"'
