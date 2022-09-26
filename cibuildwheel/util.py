from __future__ import annotations

import contextlib
import fnmatch
import itertools
import os
import re
import shlex
import ssl
import subprocess
import sys
import textwrap
import time
import urllib.request
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path, PurePath
from time import sleep
from typing import (
    Any,
    ClassVar,
    Generator,
    Iterable,
    Sequence,
    TextIO,
    TypeVar,
    cast,
    overload,
)

import bracex
import certifi

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from filelock import FileLock
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from platformdirs import user_cache_path

from cibuildwheel.typing import Final, Literal, PathOrStr, PlatformName

__all__ = [
    "resources_dir",
    "MANYLINUX_ARCHS",
    "call",
    "shell",
    "find_compatible_wheel",
    "format_safe",
    "prepare_command",
    "get_build_verbosity_extra_flags",
    "read_python_configs",
    "selector_matches",
    "strtobool",
    "cached_property",
    "chdir",
    "split_config_settings",
]

resources_dir: Final[Path] = Path(__file__).parent / "resources"

install_certifi_script: Final[Path] = resources_dir / "install_certifi.py"

BuildFrontend = Literal["pip", "build"]

MANYLINUX_ARCHS: Final[tuple[str, ...]] = (
    "x86_64",
    "i686",
    "pypy_x86_64",
    "aarch64",
    "ppc64le",
    "s390x",
    "pypy_aarch64",
    "pypy_i686",
)

MUSLLINUX_ARCHS: Final[tuple[str, ...]] = (
    "x86_64",
    "i686",
    "aarch64",
    "ppc64le",
    "s390x",
)

DEFAULT_CIBW_CACHE_PATH: Final[Path] = user_cache_path(appname="cibuildwheel", appauthor="pypa")
CIBW_CACHE_PATH: Final[Path] = Path(
    os.environ.get("CIBW_CACHE_PATH", DEFAULT_CIBW_CACHE_PATH)
).resolve()

IS_WIN: Final[bool] = sys.platform.startswith("win")


@overload
def call(
    *args: PathOrStr,
    env: dict[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: Literal[False] = ...,
) -> None:
    ...


@overload
def call(
    *args: PathOrStr,
    env: dict[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: Literal[True],
) -> str:
    ...


def call(
    *args: PathOrStr,
    env: dict[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: bool = False,
) -> str | None:
    """
    Run subprocess.run, but print the commands first. Takes the commands as
    *args. Uses shell=True on Windows due to a bug. Also converts to
    Paths to strings, due to Windows behavior at least on older Pythons.
    https://bugs.python.org/issue8557
    """
    args_ = [str(arg) for arg in args]
    # print the command executing for the logs
    print("+ " + " ".join(shlex.quote(a) for a in args_))
    kwargs: dict[str, Any] = {}
    if capture_stdout:
        kwargs["universal_newlines"] = True
        kwargs["stdout"] = subprocess.PIPE
    result = subprocess.run(args_, check=True, shell=IS_WIN, env=env, cwd=cwd, **kwargs)
    if not capture_stdout:
        return None
    return cast(str, result.stdout)


def shell(*commands: str, env: dict[str, str] | None = None, cwd: PathOrStr | None = None) -> None:
    command = " ".join(commands)
    print(f"+ {command}")
    subprocess.run(command, env=env, cwd=cwd, shell=True, check=True)


def format_safe(template: str, **kwargs: str | os.PathLike[str]) -> str:
    """
    Works similarly to `template.format(**kwargs)`, except that unmatched
    fields in `template` are passed through untouched.

    >>> format_safe('{a} {b}', a='123')
    '123 {b}'
    >>> format_safe('{a} {b[4]:3f}', a='123')
    '123 {b[4]:3f}'

    To avoid variable expansion, precede with a single backslash e.g.
    >>> format_safe('\\{a} {b}', a='123')
    '{a} {b}'
    """

    result = template

    for key, value in kwargs.items():
        find_pattern = re.compile(
            rf"""
                (?<!\#)  # don't match if preceded by a hash
                {{  # literal open curly bracket
                {re.escape(key)}  # the field name
                }}  # literal close curly bracket
            """,
            re.VERBOSE,
        )

        result = re.sub(
            pattern=find_pattern,
            repl=str(value).replace("\\", r"\\"),
            string=result,
        )

        # transform escaped sequences into their literal equivalents
        result = result.replace(f"#{{{key}}}", f"{{{key}}}")

    return result


def prepare_command(command: str, **kwargs: PathOrStr) -> str:
    """
    Preprocesses a command by expanding variables like {python}.

    For example, used in the test_command option to specify the path to the
    project's root. Unmatched syntax will mostly be allowed through.
    """
    return format_safe(command, python="python", pip="pip", **kwargs)


def get_build_verbosity_extra_flags(level: int) -> list[str]:
    if level > 0:
        return ["-" + level * "v"]
    elif level < 0:
        return ["-" + -level * "q"]
    else:
        return []


def split_config_settings(config_settings: str) -> list[str]:
    config_settings_list = shlex.split(config_settings)
    return [f"--config-setting={setting}" for setting in config_settings_list]


def read_python_configs(config: PlatformName) -> list[dict[str, str]]:
    input_file = resources_dir / "build-platforms.toml"
    with input_file.open("rb") as f:
        loaded_file = tomllib.load(f)
    results: list[dict[str, str]] = list(loaded_file[config]["python_configurations"])
    return results


def selector_matches(patterns: str, string: str) -> bool:
    """
    Returns True if `string` is matched by any of the wildcard patterns in
    `patterns`.

    Matching is according to fnmatch, but with shell-like curly brace
    expansion. For example, 'cp{36,37}-*' would match either of 'cp36-*' or
    'cp37-*'.
    """
    patterns_list = patterns.split()
    expanded_patterns = itertools.chain.from_iterable(bracex.expand(p) for p in patterns_list)
    return any(fnmatch.fnmatch(string, pat) for pat in expanded_patterns)


# Once we require Python 3.10+, we can add kw_only=True
@dataclass(frozen=True)
class BuildSelector:
    """
    This class holds a set of build/skip patterns. You call an instance with a
    build identifier, and it returns True if that identifier should be
    included. Only call this on valid identifiers, ones that have at least 2
    numeric digits before the first dash.
    """

    build_config: str
    skip_config: str
    requires_python: SpecifierSet | None = None

    # a pattern that skips prerelease versions, when include_prereleases is False.
    PRERELEASE_SKIP: ClassVar[str] = ""
    prerelease_pythons: bool = False

    def __call__(self, build_id: str) -> bool:
        # Filter build selectors by python_requires if set
        if self.requires_python is not None:
            py_ver_str = build_id.split("-")[0]
            major = int(py_ver_str[2])
            minor = int(py_ver_str[3:])
            version = Version(f"{major}.{minor}.99")
            if not self.requires_python.contains(version):
                return False

        # filter out the prerelease pythons if self.prerelease_pythons is False
        if not self.prerelease_pythons and selector_matches(self.PRERELEASE_SKIP, build_id):
            return False

        should_build = selector_matches(self.build_config, build_id)
        should_skip = selector_matches(self.skip_config, build_id)

        return should_build and not should_skip


@dataclass(frozen=True)
class TestSelector:
    """
    A build selector that can only skip tests according to a skip pattern.
    """

    skip_config: str

    def __call__(self, build_id: str) -> bool:
        should_skip = selector_matches(self.skip_config, build_id)
        return not should_skip


# Taken from https://stackoverflow.com/a/107717
class Unbuffered:
    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def write(self, data: str) -> None:
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, data: Iterable[str]) -> None:
        self.stream.writelines(data)
        self.stream.flush()

    def __getattr__(self, attr: str) -> Any:
        return getattr(self.stream, attr)


def download(url: str, dest: Path) -> None:
    print(f"+ Download {url} to {dest}")
    dest_dir = dest.parent
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    # we've had issues when relying on the host OS' CA certificates on Windows,
    # so we use certifi (this sounds odd but requests also does this by default)
    cafile = os.environ.get("SSL_CERT_FILE", certifi.where())
    context = ssl.create_default_context(cafile=cafile)
    repeat_num = 3
    for i in range(repeat_num):
        try:
            with urllib.request.urlopen(url, context=context) as response:
                dest.write_bytes(response.read())
                return

        except OSError:
            if i == repeat_num - 1:
                raise
            sleep(3)


class DependencyConstraints:
    def __init__(self, base_file_path: Path):
        assert base_file_path.exists()
        self.base_file_path = base_file_path.resolve()

    @staticmethod
    def with_defaults() -> DependencyConstraints:
        return DependencyConstraints(base_file_path=resources_dir / "constraints.txt")

    def get_for_python_version(self, version: str) -> Path:
        version_parts = version.split(".")

        # try to find a version-specific dependency file e.g. if
        # ./constraints.txt is the base, look for ./constraints-python36.txt
        specific_stem = self.base_file_path.stem + f"-python{version_parts[0]}{version_parts[1]}"
        specific_name = specific_stem + self.base_file_path.suffix
        specific_file_path = self.base_file_path.with_name(specific_name)

        if specific_file_path.exists():
            return specific_file_path
        else:
            return self.base_file_path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.base_file_path!r})"

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, DependencyConstraints):
            return False

        return self.base_file_path == o.base_file_path


class NonPlatformWheelError(Exception):
    def __init__(self) -> None:
        message = textwrap.dedent(
            """
            cibuildwheel: Build failed because a pure Python wheel was generated.

            If you intend to build a pure-Python wheel, you don't need cibuildwheel - use
            `pip wheel -w DEST_DIR .` instead.

            If you expected a platform wheel, check your project configuration, or run
            cibuildwheel with CIBW_BUILD_VERBOSITY=1 to view build logs.
            """
        )

        super().__init__(message)


class AlreadyBuiltWheelError(Exception):
    def __init__(self, wheel_name: str) -> None:
        message = textwrap.dedent(
            f"""
            cibuildwheel: Build failed because a wheel named {wheel_name} was already generated in the current run.

            If you expected another wheel to be generated, check your project configuration, or run
            cibuildwheel with CIBW_BUILD_VERBOSITY=1 to view build logs.
            """
        )

        super().__init__(message)


def strtobool(val: str) -> bool:
    return val.lower() in {"y", "yes", "t", "true", "on", "1"}


class CIProvider(Enum):
    travis_ci = "travis"
    appveyor = "appveyor"
    circle_ci = "circle_ci"
    azure_pipelines = "azure_pipelines"
    github_actions = "github_actions"
    gitlab = "gitlab"
    cirrus_ci = "cirrus_ci"
    other = "other"


def detect_ci_provider() -> CIProvider | None:
    if "TRAVIS" in os.environ:
        return CIProvider.travis_ci
    elif "APPVEYOR" in os.environ:
        return CIProvider.appveyor
    elif "CIRCLECI" in os.environ:
        return CIProvider.circle_ci
    elif "AZURE_HTTP_USER_AGENT" in os.environ:
        return CIProvider.azure_pipelines
    elif "GITHUB_ACTIONS" in os.environ:
        return CIProvider.github_actions
    elif "GITLAB_CI" in os.environ:
        return CIProvider.gitlab
    elif "CIRRUS_CI" in os.environ:
        return CIProvider.cirrus_ci
    elif strtobool(os.environ.get("CI", "false")):
        return CIProvider.other
    else:
        return None


def unwrap(text: str) -> str:
    """
    Unwraps multi-line text to a single line
    """
    # remove initial line indent
    text = textwrap.dedent(text)
    # remove leading/trailing whitespace
    text = text.strip()
    # remove consecutive whitespace
    return re.sub(r"\s+", " ", text)


@dataclass(frozen=True)
class FileReport:
    name: str
    size: str


@contextlib.contextmanager
def print_new_wheels(msg: str, output_dir: Path) -> Generator[None, None, None]:
    """
    Prints the new items in a directory upon exiting. The message to display
    can include {n} for number of wheels, {s} for total number of seconds,
    and/or {m} for total number of minutes. Does not print anything if this
    exits via exception.
    """

    start_time = time.time()
    existing_contents = set(output_dir.iterdir())
    yield
    final_contents = set(output_dir.iterdir())

    new_contents = [
        FileReport(wheel.name, f"{(wheel.stat().st_size + 1023) // 1024:,d}")
        for wheel in final_contents - existing_contents
    ]

    if len(new_contents) == 0:
        return

    max_name_len = max(len(f.name) for f in new_contents)
    max_size_len = max(len(f.size) for f in new_contents)
    n = len(new_contents)
    s = time.time() - start_time
    m = s / 60
    print(
        msg.format(n=n, s=s, m=m),
        *sorted(
            f"  {f.name:<{max_name_len}s}   {f.size:>{max_size_len}s} kB" for f in new_contents
        ),
        sep="\n",
    )


def get_pip_version(env: dict[str, str]) -> str:
    versions_output_text = call(
        "python", "-m", "pip", "freeze", "--all", capture_stdout=True, env=env
    )
    (pip_version,) = (
        version[5:]
        for version in versions_output_text.strip().splitlines()
        if version.startswith("pip==")
    )
    return pip_version


@lru_cache(maxsize=None)
def _ensure_virtualenv() -> Path:
    input_file = resources_dir / "virtualenv.toml"
    with input_file.open("rb") as f:
        loaded_file = tomllib.load(f)
    version = str(loaded_file["version"])
    url = str(loaded_file["url"])
    path = CIBW_CACHE_PATH / f"virtualenv-{version}.pyz"
    with FileLock(str(path) + ".lock"):
        if not path.exists():
            download(url, path)
    return path


def _parse_constraints_for_virtualenv(
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
    packages = ["pip", "setuptools", "wheel"]
    constraints_dict = {package: "embed" for package in packages}
    if len(dependency_constraint_flags) == 2:
        assert dependency_constraint_flags[0] == "-c"
        constraint_path = Path(dependency_constraint_flags[1])
        assert constraint_path.exists()
        with constraint_path.open(encoding="utf-8") as constraint_file:
            for line in constraint_file:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line.startswith("#"):
                    continue
                try:
                    requirement = Requirement(line)
                    package = requirement.name
                    if (
                        package not in packages
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
    python: Path, venv_path: Path, dependency_constraint_flags: Sequence[PathOrStr]
) -> dict[str, str]:
    assert python.exists()
    virtualenv_app = _ensure_virtualenv()
    constraints = _parse_constraints_for_virtualenv(dependency_constraint_flags)
    additional_flags = [f"--{package}={version}" for package, version in constraints.items()]

    # Using symlinks to pre-installed seed packages is really the fastest way to get a virtual
    # environment. The initial cost is a bit higher but reusing is much faster.
    # Windows does not always allow symlinks so just disabling for now.
    # Requires pip>=19.3 so disabling for "embed" because this means we don't know what's the
    # version of pip that will end-up installed.
    # c.f. https://virtualenv.pypa.io/en/latest/cli_interface.html#section-seeder
    if (
        not IS_WIN
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
    if IS_WIN:
        paths = [str(venv_path), str(venv_path / "Scripts")]
    else:
        paths = [str(venv_path / "bin")]
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(paths + [env["PATH"]])
    return env


T = TypeVar("T", bound=PurePath)


def find_compatible_wheel(wheels: Sequence[T], identifier: str) -> T | None:
    """
    Finds a wheel with an abi3 or a none ABI tag in `wheels` compatible with the Python interpreter
    specified by `identifier` that is previously built.
    """

    interpreter, platform = identifier.split("-")
    for wheel in wheels:
        _, _, _, tags = parse_wheel_filename(wheel.name)
        for tag in tags:
            if tag.abi == "abi3":
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
                if not tag.platform == platform:
                    continue

            # If all the filters above pass, then the wheel is a previously built compatible wheel.
            return wheel

    return None


if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from .functools_cached_property_38 import cached_property


# Can be replaced by contextlib.chdir in Python 3.11
@contextlib.contextmanager
def chdir(new_path: Path | str) -> Generator[None, None, None]:
    """Non thread-safe context manager to change the current working directory."""

    cwd = os.getcwd()
    try:
        os.chdir(new_path)
        yield
    finally:
        os.chdir(cwd)
