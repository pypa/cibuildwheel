import argparse
import os
import sys
import textwrap
from typing import List, Set, Union

import cibuildwheel
import cibuildwheel.linux
import cibuildwheel.macos
import cibuildwheel.util
import cibuildwheel.windows
from cibuildwheel.architecture import Architecture, allowed_architectures_check
from cibuildwheel.options import CommandLineArguments, Options, compute_options
from cibuildwheel.typing import PLATFORMS, PlatformName, assert_never
from cibuildwheel.util import BuildSelector, Unbuffered, detect_ci_provider


def main() -> None:
    platform: PlatformName

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
        default=os.environ.get("CIBW_PLATFORM", "auto"),
        help="""
            Platform to build for. For "linux" you need docker running, on Mac
            or Linux. For "macos", you need a Mac machine, and note that this
            script is going to automatically install MacPython on your system,
            so don't run on your development machine. For "windows", you need to
            run in Windows, and it will build and test for all versions of
            Python. Default: auto.
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
        "--output-dir",
        help="Destination folder for the wheels.",
    )

    parser.add_argument(
        "--config-file",
        help="""
            TOML config file for cibuildwheel. Defaults to pyproject.toml, but
            can be overridden with this option.
        """,
    )

    parser.add_argument(
        "package_dir",
        default=".",
        nargs="?",
        help="""
            Path to the package that you want wheels for. Must be a subdirectory of
            the working directory. When set, the working directory is still
            considered the 'project' and is copied into the Docker container on
            Linux. Default: the working directory.
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

    args = parser.parse_args(namespace=CommandLineArguments())

    if args.platform != "auto":
        platform = args.platform
    else:
        ci_provider = detect_ci_provider()
        if ci_provider is None:
            print(
                textwrap.dedent(
                    """
                    cibuildwheel: Unable to detect platform. cibuildwheel should run on your CI server;
                    Travis CI, AppVeyor, Azure Pipelines, GitHub Actions, CircleCI, and Gitlab are
                    supported. You can run on your development machine or other CI providers using the
                    --platform argument. Check --help output for more information.
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

    if platform not in PLATFORMS:
        print(f"cibuildwheel: Unsupported platform: {platform}", file=sys.stderr)
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
    # This needs to be passed on to the docker container in linux.py
    os.environ["CIBUILDWHEEL"] = "1"

    # Python is buffering by default when running on the CI platforms, giving problems interleaving subprocess call output with unflushed calls to 'print'
    sys.stdout = Unbuffered(sys.stdout)  # type: ignore[no-untyped-call,assignment]

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

    with cibuildwheel.util.print_new_wheels(
        "\n{n} wheels produced in {m:.0f} minutes:", output_dir
    ):
        if platform == "linux":
            cibuildwheel.linux.build(options)
        elif platform == "windows":
            cibuildwheel.windows.build(options)
        elif platform == "macos":
            cibuildwheel.macos.build(options)
        else:
            assert_never(platform)


def print_preamble(platform: str, options: Options, identifiers: List[str]) -> None:
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

    warnings = detect_warnings(platform=platform, options=options, identifiers=identifiers)
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print("  " + warning)

    print("\nHere we go!\n")


def get_build_identifiers(
    platform: PlatformName, build_selector: BuildSelector, architectures: Set[Architecture]
) -> List[str]:
    python_configurations: Union[
        List[cibuildwheel.linux.PythonConfiguration],
        List[cibuildwheel.windows.PythonConfiguration],
        List[cibuildwheel.macos.PythonConfiguration],
    ]

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


def detect_warnings(platform: str, options: Options, identifiers: List[str]) -> List[str]:
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
