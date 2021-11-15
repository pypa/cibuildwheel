import contextlib
import fnmatch
import itertools
import os
import re
import ssl
import subprocess
import sys
import textwrap
import time
import urllib.request
from enum import Enum
from pathlib import Path
from time import sleep
from typing import Any, Dict, Iterable, Iterator, List, Optional, TextIO

import bracex
import certifi
import tomli
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .typing import Literal, PathOrStr, PlatformName

resources_dir = Path(__file__).parent / "resources"

install_certifi_script = resources_dir / "install_certifi.py"

BuildFrontend = Literal["pip", "build"]

MANYLINUX_ARCHS = (
    "x86_64",
    "i686",
    "pypy_x86_64",
    "aarch64",
    "ppc64le",
    "s390x",
    "pypy_aarch64",
    "pypy_i686",
)

MUSLLINUX_ARCHS = (
    "x86_64",
    "i686",
    "aarch64",
    "ppc64le",
    "s390x",
)


def format_safe(template: str, **kwargs: Any) -> str:
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
            fr"""
                (?<!\#)  # don't match if preceded by a hash
                {{  # literal open curly bracket
                {re.escape(key)}  # the field name
                }}  # literal close curly bracket
            """,
            re.VERBOSE,
        )

        # we use a lambda for repl to prevent re.sub interpreting backslashes
        # in repl as escape sequences
        result = re.sub(
            pattern=find_pattern,
            repl=lambda _: str(value),
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


def get_build_verbosity_extra_flags(level: int) -> List[str]:
    if level > 0:
        return ["-" + level * "v"]
    elif level < 0:
        return ["-" + -level * "q"]
    else:
        return []


def read_python_configs(config: PlatformName) -> List[Dict[str, str]]:
    input_file = resources_dir / "build-platforms.toml"
    with input_file.open("rb") as f:
        loaded_file = tomli.load(f)
    results: List[Dict[str, str]] = list(loaded_file[config]["python_configurations"])
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


class IdentifierSelector:
    """
    This class holds a set of build/skip patterns. You call an instance with a
    build identifier, and it returns True if that identifier should be
    included. Only call this on valid identifiers, ones that have at least 2
    numeric digits before the first dash. If a pre-release version X.Y is present,
    you can filter it with prerelease="XY".
    """

    # a pattern that skips prerelease versions, when include_prereleases is False.
    PRERELEASE_SKIP = ""

    def __init__(
        self,
        *,
        build_config: str,
        skip_config: str,
        requires_python: Optional[SpecifierSet] = None,
        prerelease_pythons: bool = False,
    ):
        self.build_config = build_config
        self.skip_config = skip_config
        self.requires_python = requires_python
        self.prerelease_pythons = prerelease_pythons

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
        if not self.prerelease_pythons and selector_matches(
            BuildSelector.PRERELEASE_SKIP, build_id
        ):
            return False

        should_build = selector_matches(self.build_config, build_id)
        should_skip = selector_matches(self.skip_config, build_id)

        return should_build and not should_skip

    def __repr__(self) -> str:
        result = f"{self.__class__.__name__}(build_config={self.build_config!r}"

        if self.skip_config:
            result += f", skip_config={self.skip_config!r}"
        if self.prerelease_pythons:
            result += ", prerelease_pythons=True"

        result += ")"

        return result


class BuildSelector(IdentifierSelector):
    pass


# Note that requires-python is not needed for TestSelector, as you can't test
# what you can't build.
class TestSelector(IdentifierSelector):
    def __init__(self, *, skip_config: str):
        super().__init__(build_config="*", skip_config=skip_config)


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
            response = urllib.request.urlopen(url, context=context)
        except Exception:
            if i == repeat_num - 1:
                raise
            sleep(3)
            continue
        break

    try:
        dest.write_bytes(response.read())
    finally:
        response.close()


class DependencyConstraints:
    def __init__(self, base_file_path: Path):
        assert base_file_path.exists()
        self.base_file_path = base_file_path.resolve()

    @staticmethod
    def with_defaults() -> "DependencyConstraints":
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


def strtobool(val: str) -> bool:
    return val.lower() in {"y", "yes", "t", "true", "on", "1"}


class CIProvider(Enum):
    travis_ci = "travis"
    appveyor = "appveyor"
    circle_ci = "circle_ci"
    azure_pipelines = "azure_pipelines"
    github_actions = "github_actions"
    gitlab = "gitlab"
    other = "other"


def detect_ci_provider() -> Optional[CIProvider]:
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


@contextlib.contextmanager
def print_new_wheels(msg: str, output_dir: Path) -> Iterator[None]:
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
    new_contents = final_contents - existing_contents
    n = len(new_contents)
    s = time.time() - start_time
    m = s / 60
    print(msg.format(n=n, s=s, m=m), *sorted(f"  {f.name}" for f in new_contents), sep="\n")


def get_pip_version(env: Dict[str, str]) -> str:
    # we use shell=True here for windows, even though we don't need a shell due to a bug
    # https://bugs.python.org/issue8557
    shell = sys.platform.startswith("win")
    versions_output_text = subprocess.check_output(
        ["python", "-m", "pip", "freeze", "--all"], universal_newlines=True, shell=shell, env=env
    )
    (pip_version,) = (
        version[5:]
        for version in versions_output_text.strip().splitlines()
        if version.startswith("pip==")
    )
    return pip_version
