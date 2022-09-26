from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
import textwrap
import typing
from pathlib import Path
from tempfile import mkdtemp

import cibuildwheel
import cibuildwheel.linux
import cibuildwheel.macos
import cibuildwheel.util
import cibuildwheel.windows
from cibuildwheel.architecture import Architecture, allowed_architectures_check
from cibuildwheel.logger import log
from cibuildwheel.options import CommandLineArguments, Options, compute_options
from cibuildwheel.typing import PLATFORMS, PlatformName, assert_never
from cibuildwheel.util import (
    CIBW_CACHE_PATH,
    BuildSelector,
    Unbuffered,
    chdir,
    detect_ci_provider,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build wheels for all the platforms.",
        epilog="""
            Most options are supplied via environment variables or in
            --config-file (pyproject.toml usually). See
            https://github.com/pypa/cibuildwheel#options for info.
        """,
    )

    parser.add_argument(
        "--platform",
        choices=["auto", "linux", "macos", "windows"],
        default=None,
        help="""
            Platform to build for. Use this option to override the
            auto-detected platform or to run cibuildwheel on your development
            machine. Specifying "macos" or "windows" only works on that
            operating system, but "linux" works on all three, as long as
            Docker/Podman is installed. Default: auto.
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
        default=Path("."),
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
        "--prerelease-pythons",
        action="store_true",
        help="Enable pre-release Python versions if available.",
    )

    args = CommandLineArguments(**vars(parser.parse_args()))

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

        with chdir(temp_dir):
            build_in_directory(args)
    finally:
        # avoid https://github.com/python/cpython/issues/86962 by performing
        # cleanup manually
        shutil.rmtree(temp_dir, ignore_errors=sys.platform.startswith("win"))
        if temp_dir.exists():
            log.warning(f"Can't delete temporary folder '{str(temp_dir)}'")


def build_in_directory(args: CommandLineArguments) -> None:
    platform_option_value = args.platform or os.environ.get("CIBW_PLATFORM", "auto")
    platform: PlatformName

    if args.only:
        if "linux_" in args.only:
            platform = "linux"
        elif "macosx_" in args.only:
            platform = "macos"
        elif "win_" in args.only or "win32" in args.only:
            platform = "windows"
        else:
            print(
                f"Invalid --only='{args.only}', must be a build selector with a known platform",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.platform is not None:
            print(
                "--platform cannot be specified with --only, it is computed from --only",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.archs is not None:
            print(
                "--arch cannot be specified with --only, it is computed from --only",
                file=sys.stderr,
            )
            sys.exit(2)
    elif platform_option_value != "auto":
        if platform_option_value not in PLATFORMS:
            print(f"cibuildwheel: Unsupported platform: {platform_option_value}", file=sys.stderr)
            sys.exit(2)

        platform = typing.cast(PlatformName, platform_option_value)
    else:
        ci_provider = detect_ci_provider()
        if ci_provider is None:
            print(
                textwrap.dedent(
                    """
                    cibuildwheel: Unable to detect platform. cibuildwheel should run on your CI server;
                    Travis CI, AppVeyor, Azure Pipelines, GitHub Actions, CircleCI, Gitlab, and Cirrus CI
                    are supported. You can run on your development machine or other CI providers
                    using the --platform argument. Check --help output for more information.
                    """
                ),
                file=sys.stderr,
            )
            sys.exit(2)
        if sys.platform.startswith("linux"):
            platform = "linux"
        elif sys.platform == "darwin":
            platform = "macos"
        elif sys.platform == "win32":
            platform = "windows"
        else:
            print(
                'cibuildwheel: Unable to detect platform from "sys.platform" in a CI environment. You can run '
                "cibuildwheel using the --platform argument. Check --help output for more information.",
                file=sys.stderr,
            )
            sys.exit(2)

    options = compute_options(platform=platform, command_line_arguments=args)

    package_dir = options.globals.package_dir
    package_files = {"setup.py", "setup.cfg", "pyproject.toml"}

    if not any(package_dir.joinpath(name).exists() for name in package_files):
        names = ", ".join(sorted(package_files, reverse=True))
        msg = f"cibuildwheel: Could not find any of {{{names}}} at root of package"
        print(msg, file=sys.stderr)
        sys.exit(2)

    identifiers = get_build_identifiers(
        platform=platform,
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    if args.print_build_identifiers:
        for identifier in identifiers:
            print(identifier)
        sys.exit(0)

    # Add CIBUILDWHEEL environment variable
    os.environ["CIBUILDWHEEL"] = "1"

    # Python is buffering by default when running on the CI platforms, giving problems interleaving subprocess call output with unflushed calls to 'print'
    sys.stdout = Unbuffered(sys.stdout)  # type: ignore[assignment]

    # create the cache dir before it gets printed & builds performed
    CIBW_CACHE_PATH.mkdir(parents=True, exist_ok=True)

    print_preamble(platform=platform, options=options, identifiers=identifiers)

    try:
        options.check_for_invalid_configuration(identifiers)
        allowed_architectures_check(platform, options.globals.architectures)
    except ValueError as err:
        print("cibuildwheel:", *err.args, file=sys.stderr)
        sys.exit(4)

    if not identifiers:
        print(
            f"cibuildwheel: No build identifiers selected: {options.globals.build_selector}",
            file=sys.stderr,
        )
        if not args.allow_empty:
            sys.exit(3)

    output_dir = options.globals.output_dir

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    tmp_path = Path(mkdtemp(prefix="cibw-run-")).resolve(strict=True)
    try:
        with cibuildwheel.util.print_new_wheels(
            "\n{n} wheels produced in {m:.0f} minutes:", output_dir
        ):
            if platform == "linux":
                cibuildwheel.linux.build(options, tmp_path)
            elif platform == "windows":
                cibuildwheel.windows.build(options, tmp_path)
            elif platform == "macos":
                cibuildwheel.macos.build(options, tmp_path)
            else:
                assert_never(platform)
    finally:
        # avoid https://github.com/python/cpython/issues/86962 by performing
        # cleanup manually
        shutil.rmtree(tmp_path, ignore_errors=sys.platform.startswith("win"))
        if tmp_path.exists():
            log.warning(f"Can't delete temporary folder '{str(tmp_path)}'")


def print_preamble(platform: str, options: Options, identifiers: list[str]) -> None:
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
    print(f"  platform: {platform!r}")
    print(textwrap.indent(options.summary(identifiers), "  "))

    print(f"Cache folder: {CIBW_CACHE_PATH}")

    warnings = detect_warnings(options=options, identifiers=identifiers)
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print("  " + warning)

    print("\nHere we go!\n")


def get_build_identifiers(
    platform: PlatformName, build_selector: BuildSelector, architectures: set[Architecture]
) -> list[str]:
    python_configurations: (
        list[cibuildwheel.linux.PythonConfiguration]
        | list[cibuildwheel.windows.PythonConfiguration]
        | list[cibuildwheel.macos.PythonConfiguration]
    )

    if platform == "linux":
        python_configurations = cibuildwheel.linux.get_python_configurations(
            build_selector, architectures
        )
    elif platform == "windows":
        python_configurations = cibuildwheel.windows.get_python_configurations(
            build_selector, architectures
        )
    elif platform == "macos":
        python_configurations = cibuildwheel.macos.get_python_configurations(
            build_selector, architectures
        )
    else:
        assert_never(platform)

    return [config.identifier for config in python_configurations]


def detect_warnings(*, options: Options, identifiers: list[str]) -> list[str]:
    warnings = []

    # warn about deprecated {python} and {pip}
    for option_name in ["test_command", "before_build"]:
        option_values = [getattr(options.build_options(i), option_name) for i in identifiers]

        if any(o and ("{python}" in o or "{pip}" in o) for o in option_values):
            # Reminder: in an f-string, double braces means literal single brace
            msg = (
                f"{option_name}: '{{python}}' and '{{pip}}' are no longer needed, "
                "and will be removed in a future release. Simply use 'python' or 'pip' instead."
            )
            warnings.append(msg)

    return warnings


if __name__ == "__main__":
    main()
