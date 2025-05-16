import argparse
import contextlib
import dataclasses
import functools
import os
import shutil
import sys
import tarfile
import textwrap
import time
import traceback
import typing
from collections.abc import Generator, Iterable, Sequence
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Literal, TextIO

import cibuildwheel
import cibuildwheel.util
from cibuildwheel import errors
from cibuildwheel.architecture import Architecture, allowed_architectures_check
from cibuildwheel.ci import CIProvider, detect_ci_provider, fix_ansi_codes_for_github_actions
from cibuildwheel.logger import log
from cibuildwheel.options import CommandLineArguments, Options, compute_options
from cibuildwheel.platforms import ALL_PLATFORM_MODULES, get_build_identifiers
from cibuildwheel.selector import BuildSelector, EnableGroup, selector_matches
from cibuildwheel.typing import PLATFORMS, PlatformName
from cibuildwheel.util.file import CIBW_CACHE_PATH
from cibuildwheel.util.helpers import strtobool


@dataclasses.dataclass
class GlobalOptions:
    print_traceback_on_error: bool = True  # decides what happens when errors are hit.


@dataclasses.dataclass(frozen=True)
class FileReport:
    name: str
    size: str


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


def main() -> None:
    global_options = GlobalOptions()
    try:
        main_inner(global_options)
    except errors.FatalError as e:
        message = e.args[0]
        if log.step_active:
            log.step_end_with_error(message)
        else:
            log.error(message)

        if global_options.print_traceback_on_error:
            traceback.print_exc(file=sys.stderr)

        sys.exit(e.return_code)


def main_inner(global_options: GlobalOptions) -> None:
    """
    `main_inner` is the same as `main`, but it raises FatalError exceptions
    rather than exiting directly.
    """

    make_parser = functools.partial(argparse.ArgumentParser, allow_abbrev=False)
    if sys.version_info >= (3, 14):
        make_parser = functools.partial(make_parser, color=True, suggest_on_error=True)
    parser = make_parser(
        description="Build wheels for all the platforms.",
        epilog="""
            Most options are supplied via environment variables or in
            --config-file (pyproject.toml usually). See
            https://github.com/pypa/cibuildwheel#options for info.
        """,
    )

    parser.add_argument(
        "--platform",
        choices=["auto", "linux", "macos", "windows", "pyodide", "ios"],
        default=None,
        help="""
            Platform to build for. Use this option to override the auto-detected
            platform. Specifying "macos" or "windows" only works on that
            operating system. "linux" works on any desktop OS, as long as
            Docker/Podman is installed. "pyodide" only works on linux and macOS.
            "ios" only work on macOS. Default: auto.
        """,
    )

    arch_list_str = ", ".join(a.name for a in Architecture)
    parser.add_argument(
        "--archs",
        default=None,
        help=f"""
            Comma-separated list of CPU architectures to build for.
            When set to 'auto', builds the architectures natively supported
            on this machine. Set this option to build an architecture
            via emulation, for example, using binfmt_misc and QEMU.
            Default: auto.
            Choices: auto, auto64, auto32, native, all, {arch_list_str}
        """,
    )

    enable_groups_str = ", ".join(g.value for g in EnableGroup)
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        metavar="GROUP",
        help=f"""
            Enable an additional category of builds. Use multiple times to select multiple groups. Choices: {enable_groups_str}.
        """,
    )

    parser.add_argument(
        "--only",
        default=None,
        help="""
            Force a single wheel build when given an identifier. Overrides
            CIBW_BUILD/CIBW_SKIP. --platform and --arch cannot be specified
            if this is given.
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("CIBW_OUTPUT_DIR", "wheelhouse")),
        help="Destination folder for the wheels. Default: wheelhouse.",
    )

    parser.add_argument(
        "--config-file",
        default="",
        help="""
            TOML config file. Default: "", meaning {package}/pyproject.toml, if
            it exists. To refer to a project inside your project, use {package};
            this matters if you build from an SDist.
        """,
    )

    parser.add_argument(
        "package_dir",
        metavar="PACKAGE",
        default=Path(),
        type=Path,
        nargs="?",
        help="""
            Path to the package that you want wheels for. Default: the working
            directory. Can be a directory inside the working directory, or an
            sdist. When set to a directory, the working directory is still
            considered the 'project' and is copied into the build container
            on Linux.  When set to a tar.gz sdist file, --config-file
            and --output-dir are relative to the current directory, and other
            paths are relative to the expanded SDist directory.
        """,
    )

    parser.add_argument(
        "--print-build-identifiers",
        action="store_true",
        help="Print the build identifiers matched by the current invocation and exit.",
    )

    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Do not report an error code if the build does not match any wheels.",
    )

    parser.add_argument(
        "--debug-traceback",
        action="store_true",
        default=strtobool(os.environ.get("CIBW_DEBUG_TRACEBACK", "0")),
        help="Print a full traceback for all errors",
    )

    args = CommandLineArguments(**vars(parser.parse_args()))

    global_options.print_traceback_on_error = args.debug_traceback

    args.package_dir = args.package_dir.resolve()

    # This are always relative to the base directory, even in SDist builds
    args.output_dir = args.output_dir.resolve()

    # Standard builds if a directory or non-existent path is given
    if not args.package_dir.is_file() and not args.package_dir.name.endswith("tar.gz"):
        build_in_directory(args)
        return

    # Tarfile builds require extraction and changing the directory
    temp_dir = Path(mkdtemp(prefix="cibw-sdist-")).resolve(strict=True)
    try:
        with tarfile.open(args.package_dir) as tar:
            tar.extractall(path=temp_dir)

        # The extract directory is now the project dir
        try:
            (project_dir,) = temp_dir.iterdir()
        except ValueError:
            msg = "invalid sdist: didn't contain a single dir"
            raise SystemExit(msg) from None

        # This is now the new package dir
        args.package_dir = project_dir.resolve()

        with contextlib.chdir(project_dir):
            build_in_directory(args)
    finally:
        # avoid https://github.com/python/cpython/issues/86962 by performing
        # cleanup manually
        shutil.rmtree(temp_dir, ignore_errors=sys.platform.startswith("win"))
        if temp_dir.exists():
            log.warning(f"Can't delete temporary folder '{temp_dir}'")


def _compute_platform_only(only: str) -> PlatformName:
    if "linux_" in only:
        return "linux"
    if "macosx_" in only:
        return "macos"
    if "win_" in only or "win32" in only:
        return "windows"
    if "pyodide_" in only:
        return "pyodide"
    if "ios_" in only:
        return "ios"
    msg = f"Invalid --only='{only}', must be a build selector with a known platform"
    raise errors.ConfigurationError(msg)


def _compute_platform_auto() -> PlatformName:
    if sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    else:
        msg = (
            'Unable to detect platform from "sys.platform". cibuildwheel doesn\'t '
            "support building wheels for this platform. You might be able to build for a different "
            "platform using the --platform argument. Check --help output for more information."
        )
        raise errors.ConfigurationError(msg)


def _compute_platform(args: CommandLineArguments) -> PlatformName:
    platform_option_value = args.platform or os.environ.get("CIBW_PLATFORM", "") or "auto"

    if args.only and args.platform is not None:
        msg = "--platform cannot be specified with --only, it is computed from --only"
        raise errors.ConfigurationError(msg)
    if args.only and args.archs is not None:
        msg = "--arch cannot be specified with --only, it is computed from --only"
        raise errors.ConfigurationError(msg)

    if platform_option_value not in PLATFORMS | {"auto"}:
        msg = f"Unsupported platform: {platform_option_value}"
        raise errors.ConfigurationError(msg)

    if args.only:
        return _compute_platform_only(args.only)
    elif platform_option_value != "auto":
        return typing.cast(PlatformName, platform_option_value)

    return _compute_platform_auto()


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

    if not new_contents:
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


def build_in_directory(args: CommandLineArguments) -> None:
    platform: PlatformName = _compute_platform(args)
    if platform == "pyodide" and sys.platform == "win32":
        msg = "Building for pyodide is not supported on Windows"
        raise errors.ConfigurationError(msg)

    options = compute_options(platform=platform, command_line_arguments=args, env=os.environ)

    package_dir = options.globals.package_dir
    package_files = {"setup.py", "setup.cfg", "pyproject.toml"}

    if not any(package_dir.joinpath(name).exists() for name in package_files):
        names = ", ".join(sorted(package_files, reverse=True))
        msg = f"Could not find any of {{{names}}} at root of package"
        raise errors.ConfigurationError(msg)

    platform_module = ALL_PLATFORM_MODULES[platform]
    identifiers = get_build_identifiers(
        platform_module=platform_module,
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    if args.print_build_identifiers:
        for identifier in identifiers:
            print(identifier)
        sys.exit(0)

    # Add CIBUILDWHEEL environment variable
    os.environ["CIBUILDWHEEL"] = "1"

    # Python is buffering by default when running on the CI platforms, giving
    # problems interleaving subprocess call output with unflushed calls to
    # 'print'
    sys.stdout = Unbuffered(sys.stdout)

    # create the cache dir before it gets printed & builds performed
    CIBW_CACHE_PATH.mkdir(parents=True, exist_ok=True)

    print_preamble(platform=platform, options=options, identifiers=identifiers)

    try:
        options.check_for_invalid_configuration(identifiers)
        allowed_architectures_check(platform, options.globals.architectures)
    except ValueError as err:
        raise errors.DeprecationError(*err.args) from err

    if not identifiers:
        message = f"No build identifiers selected: {options.globals.build_selector}"
        if options.globals.allow_empty:
            print(f"cibuildwheel: {message}", file=sys.stderr)
        else:
            raise errors.NothingToDoError(message)

    output_dir = options.globals.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    tmp_path = Path(mkdtemp(prefix="cibw-run-")).resolve(strict=True)
    try:
        with print_new_wheels("\n{n} wheels produced in {m:.0f} minutes:", output_dir):
            platform_module.build(options, tmp_path)
    finally:
        # avoid https://github.com/python/cpython/issues/86962 by performing
        # cleanup manually
        shutil.rmtree(tmp_path, ignore_errors=sys.platform.startswith("win"))
        if tmp_path.exists():
            log.warning(f"Can't delete temporary folder '{tmp_path}'")


def print_preamble(platform: str, options: Options, identifiers: Sequence[str]) -> None:
    print(
        textwrap.dedent(
            """
                 _ _       _ _   _       _           _
             ___|_| |_ _ _|_| |_| |_ _ _| |_ ___ ___| |
            |  _| | . | | | | | . | | | |   | -_| -_| |
            |___|_|___|___|_|_|___|_____|_|_|___|___|_|
            """
        )
    )

    print(f"cibuildwheel version {cibuildwheel.__version__}\n")

    print("Build options:")
    print(f"  platform: {platform}")
    options_summary = textwrap.indent(options.summary(identifiers), "  ")
    if detect_ci_provider() == CIProvider.github_actions:
        options_summary = fix_ansi_codes_for_github_actions(options_summary)
    print(options_summary)

    print()
    print(f"Cache folder: {CIBW_CACHE_PATH}")
    print()

    warnings = detect_warnings(options=options, identifiers=identifiers)
    for warning in warnings:
        log.warning(warning)

    print("Here we go!\n")


def detect_warnings(*, options: Options, identifiers: Iterable[str]) -> list[str]:
    warnings = []

    python_version_deprecation = ((3, 11), 3)
    if sys.version_info[:2] < python_version_deprecation[0]:
        python_version = ".".join(map(str, python_version_deprecation[0]))
        msg = (
            f"cibuildwheel {python_version_deprecation[1]} will require Python {python_version}+, "
            "please upgrade the Python version used to run cibuildwheel. "
            "This does not affect the versions you can target when building wheels. See: https://cibuildwheel.pypa.io/en/stable/#what-does-it-do"
        )
        warnings.append(msg)

    # warn about deprecated {python} and {pip}
    for option_name in ["test_command", "before_build"]:
        option_values = [getattr(options.build_options(i), option_name) for i in identifiers]

        if any(o and ("{python}" in o or "{pip}" in o) for o in option_values):
            # Reminder: in an f-string, double braces means literal single brace
            msg = (
                f"{option_name}: '{{python}}' and '{{pip}}' are no longer supported "
                "and have been removed in cibuildwheel 3. Simply use 'python' or 'pip' instead."
            )
            raise errors.ConfigurationError(msg)

    build_selector = options.globals.build_selector
    test_selector = options.globals.test_selector

    all_valid_identifiers = [
        config.identifier
        for module in ALL_PLATFORM_MODULES.values()
        for config in module.all_python_configurations()
    ]

    enabled_selector = BuildSelector(
        build_config="*", skip_config="", enable=options.globals.build_selector.enable
    )
    all_enabled_identifiers = [
        identifier for identifier in all_valid_identifiers if enabled_selector(identifier)
    ]

    warnings += check_for_invalid_selectors(
        selector_name="build",
        selector_value=build_selector.build_config,
        all_valid_identifiers=all_valid_identifiers,
        all_enabled_identifiers=all_enabled_identifiers,
    )
    warnings += check_for_invalid_selectors(
        selector_name="skip",
        selector_value=build_selector.skip_config,
        all_valid_identifiers=all_valid_identifiers,
        all_enabled_identifiers=all_enabled_identifiers,
    )
    warnings += check_for_invalid_selectors(
        selector_name="test_skip",
        selector_value=test_selector.skip_config,
        all_valid_identifiers=all_valid_identifiers,
        all_enabled_identifiers=all_enabled_identifiers,
    )

    return warnings


def check_for_invalid_selectors(
    *,
    selector_name: Literal["build", "skip", "test_skip"],
    selector_value: str,
    all_valid_identifiers: Sequence[str],
    all_enabled_identifiers: Sequence[str],
) -> list[str]:
    warnings = []

    for selector in selector_value.split():
        if not any(selector_matches(selector, i) for i in all_enabled_identifiers):
            msg = f"Invalid {selector_name} selector: {selector!r}. "
            error_type: type = errors.ConfigurationError

            if any(selector_matches(selector, i) for i in all_valid_identifiers):
                msg += "This selector matches a group that wasn't enabled. Enable it using the `enable` option or remove this selector. "

            if "p2" in selector or "p35" in selector:
                msg += f"cibuildwheel 3.x no longer supports Python < 3.8. Please use the 1.x series or update `{selector_name}`. "
                error_type = errors.DeprecationError
            if "p36" in selector or "p37" in selector:
                msg += f"cibuildwheel 3.x no longer supports Python < 3.8. Please use the 2.x series or update `{selector_name}`. "
                error_type = errors.DeprecationError

            if selector_name == "build":
                raise error_type(msg)

            msg += "This selector will have no effect. "

            warnings.append(msg)

    return warnings


if __name__ == "__main__":
    main()
