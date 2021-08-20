import argparse
import os
import sys
import textwrap
import traceback
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from packaging.specifiers import SpecifierSet

import cibuildwheel
import cibuildwheel.linux
import cibuildwheel.macos
import cibuildwheel.util
import cibuildwheel.windows
from cibuildwheel.architecture import Architecture, allowed_architectures_check
from cibuildwheel.environment import EnvironmentParseError, parse_environment
from cibuildwheel.options import ConfigOptions
from cibuildwheel.projectfiles import get_requires_python_str
from cibuildwheel.typing import PLATFORMS, PlatformName, assert_never
from cibuildwheel.util import (
    BuildFrontend,
    BuildOptions,
    BuildSelector,
    DependencyConstraints,
    TestSelector,
    Unbuffered,
    detect_ci_provider,
    resources_dir,
)

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

    args = parser.parse_args()

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

    package_dir = Path(args.package_dir)

    manylinux_identifiers = {
        f"manylinux-{build_platform}-image" for build_platform in MANYLINUX_ARCHS
    }
    disallow = {
        "linux": {"dependency-versions"},
        "macos": manylinux_identifiers,
        "windows": manylinux_identifiers,
    }
    options = ConfigOptions(package_dir, args.config_file, platform=platform, disallow=disallow)
    output_dir = Path(
        args.output_dir
        if args.output_dir is not None
        else os.environ.get("CIBW_OUTPUT_DIR", "wheelhouse")
    )

    build_config = options("build", env_plat=False, sep=" ") or "*"
    skip_config = options("skip", env_plat=False, sep=" ")
    test_skip = options("test-skip", env_plat=False, sep=" ")

    archs_config_str = args.archs or options("archs", sep=" ")

    build_frontend_str = options("build-frontend", env_plat=False)
    environment_config = options("environment", table={"item": '{k}="{v}"', "sep": " "})
    before_all = options("before-all", sep=" && ")
    before_build = options("before-build", sep=" && ")
    repair_command = options("repair-wheel-command", sep=" && ")

    dependency_versions = options("dependency-versions")
    test_command = options("test-command", sep=" && ")
    before_test = options("before-test", sep=" && ")
    test_requires = options("test-requires", sep=" ").split()
    test_extras = options("test-extras", sep=",")
    build_verbosity_str = options("build-verbosity")

    prerelease_pythons = args.prerelease_pythons or cibuildwheel.util.strtobool(
        os.environ.get("CIBW_PRERELEASE_PYTHONS", "0")
    )

    build_frontend: BuildFrontend
    if build_frontend_str == "build":
        build_frontend = "build"
    elif build_frontend_str == "pip":
        build_frontend = "pip"
    else:
        msg = f"cibuildwheel: Unrecognised build frontend '{build_frontend}', only 'pip' and 'build' are supported"
        print(msg, file=sys.stderr)
        sys.exit(2)

    package_files = {"setup.py", "setup.cfg", "pyproject.toml"}

    if not any(package_dir.joinpath(name).exists() for name in package_files):
        names = ", ".join(sorted(package_files, reverse=True))
        msg = f"cibuildwheel: Could not find any of {{{names}}} at root of package"
        print(msg, file=sys.stderr)
        sys.exit(2)

    # This is not supported in tool.cibuildwheel, as it comes from a standard location.
    # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
    requires_python_str: Optional[str] = os.environ.get(
        "CIBW_PROJECT_REQUIRES_PYTHON"
    ) or get_requires_python_str(package_dir)
    requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

    deprecated_selectors("CIBW_BUILD", build_config, error=True)
    deprecated_selectors("CIBW_SKIP", skip_config)
    deprecated_selectors("CIBW_TEST_SKIP", test_skip)

    build_selector = BuildSelector(
        build_config=build_config,
        skip_config=skip_config,
        requires_python=requires_python,
        prerelease_pythons=prerelease_pythons,
    )
    test_selector = TestSelector(skip_config=test_skip)

    try:
        environment = parse_environment(environment_config)
    except (EnvironmentParseError, ValueError):
        print(f'cibuildwheel: Malformed environment option "{environment_config}"', file=sys.stderr)
        traceback.print_exc(None, sys.stderr)
        sys.exit(2)

    if dependency_versions == "pinned":
        dependency_constraints: Optional[
            DependencyConstraints
        ] = DependencyConstraints.with_defaults()
    elif dependency_versions == "latest":
        dependency_constraints = None
    else:
        dependency_versions_path = Path(dependency_versions)
        dependency_constraints = DependencyConstraints(dependency_versions_path)

    if test_extras:
        test_extras = f"[{test_extras}]"

    try:
        build_verbosity = min(3, max(-3, int(build_verbosity_str)))
    except ValueError:
        build_verbosity = 0

    # Add CIBUILDWHEEL environment variable
    # This needs to be passed on to the docker container in linux.py
    os.environ["CIBUILDWHEEL"] = "1"

    archs = Architecture.parse_config(archs_config_str, platform=platform)

    identifiers = get_build_identifiers(platform, build_selector, archs)

    if args.print_build_identifiers:
        for identifier in identifiers:
            print(identifier)
        sys.exit(0)

    manylinux_images: Dict[str, str] = {}
    if platform == "linux":
        pinned_docker_images_file = resources_dir / "pinned_docker_images.cfg"
        all_pinned_docker_images = ConfigParser()
        all_pinned_docker_images.read(pinned_docker_images_file)
        # all_pinned_docker_images looks like a dict of dicts, e.g.
        # { 'x86_64': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'i686': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'pypy_x86_64': {'manylinux2010': '...' }
        #   ... }

        for build_platform in MANYLINUX_ARCHS:
            pinned_images = all_pinned_docker_images[build_platform]

            config_value = options(f"manylinux-{build_platform}-image")

            if config_value is None:
                # default to manylinux2010 if it's available, otherwise manylinux2014
                image = pinned_images.get("manylinux2010") or pinned_images.get("manylinux2014")
            elif config_value in pinned_images:
                image = pinned_images[config_value]
            else:
                image = config_value

            manylinux_images[build_platform] = image

    build_options = BuildOptions(
        architectures=archs,
        package_dir=package_dir,
        output_dir=output_dir,
        test_command=test_command,
        test_requires=test_requires,
        test_extras=test_extras,
        before_test=before_test,
        before_build=before_build,
        before_all=before_all,
        build_verbosity=build_verbosity,
        build_selector=build_selector,
        test_selector=test_selector,
        repair_command=repair_command,
        environment=environment,
        dependency_constraints=dependency_constraints,
        manylinux_images=manylinux_images or None,
        build_frontend=build_frontend,
    )

    # Python is buffering by default when running on the CI platforms, giving problems interleaving subprocess call output with unflushed calls to 'print'
    sys.stdout = Unbuffered(sys.stdout)  # type: ignore

    print_preamble(platform, build_options)

    try:
        allowed_architectures_check(platform, build_options.architectures)
    except ValueError as err:
        print("cibuildwheel:", *err.args, file=sys.stderr)
        sys.exit(4)

    if not identifiers:
        print(f"cibuildwheel: No build identifiers selected: {build_selector}", file=sys.stderr)
        if not args.allow_empty:
            sys.exit(3)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    with cibuildwheel.util.print_new_wheels(
        "\n{n} wheels produced in {m:.0f} minutes:", output_dir
    ):
        if platform == "linux":
            cibuildwheel.linux.build(build_options)
        elif platform == "windows":
            cibuildwheel.windows.build(build_options)
        elif platform == "macos":
            cibuildwheel.macos.build(build_options)
        else:
            assert_never(platform)


def deprecated_selectors(name: str, selector: str, *, error: bool = False) -> None:
    if "p2" in selector or "p35" in selector:
        msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {name}"
        print(msg, file=sys.stderr)
        if error:
            sys.exit(4)


def print_preamble(platform: str, build_options: BuildOptions) -> None:
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
    for option, value in sorted(build_options._asdict().items()):
        print(f"  {option}: {value!r}")

    warnings = detect_warnings(platform, build_options)
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


def detect_warnings(platform: str, build_options: BuildOptions) -> List[str]:
    warnings = []

    # warn about deprecated {python} and {pip}
    for option_name in ["test_command", "before_build"]:
        option_value = getattr(build_options, option_name)

        if option_value and ("{python}" in option_value or "{pip}" in option_value):
            # Reminder: in an f-string, double braces means literal single brace
            msg = (
                f"{option_name}: '{{python}}' and '{{pip}}' are no longer needed, "
                "and will be removed in a future release. Simply use 'python' or 'pip' instead."
            )
            warnings.append(msg)

    return warnings


if __name__ == "__main__":
    main()
