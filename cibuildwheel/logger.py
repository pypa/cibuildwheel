import codecs
import os
import re
import sys
import time
from typing import IO, AnyStr, Final

from .ci import CIProvider, detect_ci_provider

FoldPattern = tuple[str, str]
DEFAULT_FOLD_PATTERN: Final[FoldPattern] = ("{name}", "")
FOLD_PATTERNS: Final[dict[str, FoldPattern]] = {
    "azure": ("##[group]{name}", "##[endgroup]"),
    "travis": ("travis_fold:start:{identifier}\n{name}", "travis_fold:end:{identifier}"),
    "github": ("::group::{name}", "::endgroup::{name}"),
}

PLATFORM_IDENTIFIER_DESCRIPTIONS: Final[dict[str, str]] = {
    "manylinux_x86_64": "manylinux x86_64",
    "manylinux_i686": "manylinux i686",
    "manylinux_aarch64": "manylinux aarch64",
    "manylinux_ppc64le": "manylinux ppc64le",
    "manylinux_s390x": "manylinux s390x",
    "manylinux_armv7l": "manylinux armv7l",
    "manylinux_riscv64": "manylinux riscv64",
    "musllinux_x86_64": "musllinux x86_64",
    "musllinux_i686": "musllinux i686",
    "musllinux_aarch64": "musllinux aarch64",
    "musllinux_ppc64le": "musllinux ppc64le",
    "musllinux_s390x": "musllinux s390x",
    "musllinux_armv7l": "musllinux armv7l",
    "musllinux_riscv64": "musllinux riscv64",
    "win32": "Windows 32bit",
    "win_amd64": "Windows 64bit",
    "win_arm64": "Windows on ARM 64bit",
    "macosx_x86_64": "macOS x86_64",
    "macosx_universal2": "macOS Universal 2 - x86_64 and arm64",
    "macosx_arm64": "macOS arm64 - Apple Silicon",
    "pyodide_wasm32": "Pyodide",
    "ios_arm64_iphoneos": "iOS Device (ARM64)",
    "ios_arm64_iphonesimulator": "iOS Simulator (ARM64)",
    "ios_x86_64_iphonesimulator": "iOS Simulator (x86_64)",
}


class Colors:
    def __init__(self, *, enabled: bool) -> None:
        self.red = "\033[31m" if enabled else ""
        self.green = "\033[32m" if enabled else ""
        self.yellow = "\033[33m" if enabled else ""
        self.blue = "\033[34m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.bright_red = "\033[91m" if enabled else ""
        self.bright_green = "\033[92m" if enabled else ""
        self.white = "\033[37m\033[97m" if enabled else ""
        self.gray = "\033[38;5;244m" if enabled else ""

        self.bg_grey = "\033[48;5;235m" if enabled else ""

        self.bold = "\033[1m" if enabled else ""
        self.faint = "\033[2m" if enabled else ""

        self.end = "\033[0m" if enabled else ""


class Symbols:
    def __init__(self, *, unicode: bool) -> None:
        self.done = "✓" if unicode else "done"
        self.error = "✕" if unicode else "failed"


class Logger:
    fold_mode: str
    colors_enabled: bool
    unicode_enabled: bool
    active_build_identifier: str | None = None
    build_start_time: float | None = None
    step_start_time: float | None = None
    active_fold_group_name: str | None = None

    def __init__(self) -> None:
        if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
            # the encoding on Windows can be a 1-byte charmap, but all CIs
            # support utf8, so we hardcode that
            sys.stdout.reconfigure(encoding="utf8")

        self.unicode_enabled = file_supports_unicode(sys.stdout)

        ci_provider = detect_ci_provider()

        if ci_provider == CIProvider.azure_pipelines:
            self.fold_mode = "azure"
            self.colors_enabled = True

        elif ci_provider == CIProvider.github_actions:
            self.fold_mode = "github"
            self.colors_enabled = True

        elif ci_provider == CIProvider.travis_ci:
            self.fold_mode = "travis"
            self.colors_enabled = True

        elif ci_provider == CIProvider.appveyor:
            self.fold_mode = "disabled"
            self.colors_enabled = True

        else:
            self.fold_mode = "disabled"
            self.colors_enabled = file_supports_color(sys.stdout)

    def build_start(self, identifier: str) -> None:
        self.step_end()
        c = self.colors
        description = build_description_from_identifier(identifier)
        print()
        print(f"{c.bold}{c.blue}Building {identifier} wheel{c.end}")
        print(f"{description}")
        print()

        self.build_start_time = time.time()
        self.active_build_identifier = identifier

    def build_end(self) -> None:
        assert self.build_start_time is not None
        assert self.active_build_identifier is not None
        self.step_end()

        c = self.colors
        s = self.symbols
        duration = time.time() - self.build_start_time

        print()
        print(
            f"{c.green}{s.done} {c.end}{self.active_build_identifier} finished in {duration:.2f}s"
        )
        self.build_start_time = None
        self.active_build_identifier = None

    def step(self, step_description: str) -> None:
        self.step_end()
        self.step_start_time = time.time()
        self._start_fold_group(step_description)

    def step_end(self, success: bool = True) -> None:
        if self.step_start_time is not None:
            self._end_fold_group()
            c = self.colors
            s = self.symbols
            duration = time.time() - self.step_start_time
            if success:
                print(f"{c.green}{s.done} {c.end}{duration:.2f}s".rjust(78))
            else:
                print(f"{c.red}{s.error} {c.end}{duration:.2f}s".rjust(78))

            self.step_start_time = None

    def step_end_with_error(self, error: BaseException | str) -> None:
        self.step_end(success=False)
        self.error(error)

    def quiet(self, message: str) -> None:
        c = self.colors
        print(f"{c.gray}{message}{c.end}", file=sys.stderr)

    def notice(self, message: str) -> None:
        if self.fold_mode == "github":
            print(f"::notice::cibuildwheel: {message}\n", file=sys.stderr)
        else:
            c = self.colors
            print(f"cibuildwheel: {c.bold}note{c.end}: {message}\n", file=sys.stderr)

    def warning(self, message: str) -> None:
        if self.fold_mode == "github":
            print(f"::warning::cibuildwheel: {message}\n", file=sys.stderr)
        else:
            c = self.colors
            print(f"cibuildwheel: {c.yellow}warning{c.end}: {message}\n", file=sys.stderr)

    def error(self, error: BaseException | str) -> None:
        if self.fold_mode == "github":
            print(f"::error::cibuildwheel: {error}\n", file=sys.stderr)
        else:
            c = self.colors
            print(f"cibuildwheel: {c.bright_red}error{c.end}: {error}\n", file=sys.stderr)

    @property
    def step_active(self) -> bool:
        return self.step_start_time is not None

    def _start_fold_group(self, name: str) -> None:
        self._end_fold_group()
        self.active_fold_group_name = name
        fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, DEFAULT_FOLD_PATTERN)[0]
        identifier = self._fold_group_identifier(name)

        print(fold_start_pattern.format(name=self.active_fold_group_name, identifier=identifier))
        print()
        sys.stdout.flush()

    def _end_fold_group(self) -> None:
        if self.active_fold_group_name:
            fold_start_pattern = FOLD_PATTERNS.get(self.fold_mode, DEFAULT_FOLD_PATTERN)[1]
            identifier = self._fold_group_identifier(self.active_fold_group_name)
            print(
                fold_start_pattern.format(name=self.active_fold_group_name, identifier=identifier)
            )
            sys.stdout.flush()
            self.active_fold_group_name = None

    @staticmethod
    def _fold_group_identifier(name: str) -> str:
        """
        Travis doesn't like fold groups identifiers that have spaces in. This
        method converts them to ascii identifiers
        """
        # whitespace to underscores
        identifier = re.sub(r"\s+", "_", name)
        # remove non-alphanum
        identifier = re.sub(r"[^A-Za-z\d_]+", "", identifier)
        # trim underscores
        identifier = identifier.strip("_")
        # lowercase, shorten
        return identifier.lower()[:20]

    @property
    def colors(self) -> Colors:
        return Colors(enabled=self.colors_enabled)

    @property
    def symbols(self) -> Symbols:
        return Symbols(unicode=self.unicode_enabled)


def build_description_from_identifier(identifier: str) -> str:
    python_identifier, _, platform_identifier = identifier.partition("-")

    build_description = ""

    python_interpreter = python_identifier[0:2]
    version_parts = python_identifier[2:].split("_")
    python_version = version_parts[0]

    if python_interpreter == "cp":
        build_description += "CPython"
    elif python_interpreter == "pp":
        build_description += "PyPy"
    elif python_interpreter == "gp":
        build_description += "GraalPy"
    else:
        msg = f"unknown python {python_interpreter!r}"
        raise Exception(msg)

    build_description += f" {python_version[0]}.{python_version[1:]} "
    if len(version_parts) > 1:
        build_description += f"(ABI {version_parts[1]}) "

    try:
        build_description += PLATFORM_IDENTIFIER_DESCRIPTIONS[platform_identifier]
    except KeyError as e:
        msg = f"unknown platform {platform_identifier!r}"
        raise Exception(msg) from e

    return build_description


def file_supports_color(file_obj: IO[AnyStr]) -> bool:
    """
    Returns True if the running system's terminal supports color.
    """
    plat = sys.platform
    supported_platform = plat != "win32" or "ANSICON" in os.environ

    is_a_tty = file_is_a_tty(file_obj)

    return supported_platform and is_a_tty


def file_is_a_tty(file_obj: IO[AnyStr]) -> bool:
    return hasattr(file_obj, "isatty") and file_obj.isatty()


def file_supports_unicode(file_obj: IO[AnyStr]) -> bool:
    encoding = getattr(file_obj, "encoding", None)
    if not encoding:
        return False

    codec_info = codecs.lookup(encoding)

    return "utf" in codec_info.name


# Global instance of the Logger.
# (there's only one stdout per-process, so a global instance is justified)
log = Logger()
