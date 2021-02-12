import argparse
import os
import sys
import textwrap
import traceback
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, overload

from packaging.specifiers import SpecifierSet

import cibuildwheel
import cibuildwheel.linux
import cibuildwheel.macos
import cibuildwheel.util
import cibuildwheel.windows
from cibuildwheel.architecture import Architecture, allowed_architectures_check
from cibuildwheel.environment import EnvironmentParseError, parse_environment
from cibuildwheel.projectfiles import get_requires_python_str
from cibuildwheel.typing import PLATFORMS, PlatformName, assert_never
from cibuildwheel.util import (
    BuildOptions,
    BuildSelector,
    DependencyConstraints,
    TestSelector,
    Unbuffered,
    detect_ci_provider,
    resources_dir,
)


@overload
def get_option_from_environment(option_name: str, *, platform: Optional[str] = None, default: str) -> str: ...  # noqa: E704
@overload
def get_option_from_environment(option_name: str, *, platform: Optional[str] = None, default: None = None) -> Optional[str]: ...  # noqa: E704 E302
def get_option_from_environment(option_name: str, *, platform: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:  # noqa: E302
    '''
    Returns an option from the environment, optionally scoped by the platform.

    Example:
      get_option_from_environment('CIBW_COLOR', platform='macos')

      This will return the value of CIBW_COLOR_MACOS if it exists, otherwise the value of
      CIBW_COLOR.
    '''
    if platform:
        option = os.environ.get(f'{option_name}_{platform.upper()}')
        if option is not None:
            return option

    return os.environ.get(option_name, default)


def main() -> None:
    platform: PlatformName

    parser = argparse.ArgumentParser(
        description='Build wheels for all the platforms.',
        epilog='''
            Most options are supplied via environment variables.
            See https://github.com/joerick/cibuildwheel#options for info.
        ''')

    parser.add_argument('--platform',
                        choices=['auto', 'linux', 'macos', 'windows'],
                        default=os.environ.get('CIBW_PLATFORM', 'auto'),
                        help='''
                            Platform to build for. For "linux" you need docker running, on Mac
                            or Linux. For "macos", you need a Mac machine, and note that this
                            script is going to automatically install MacPython on your system,
                            so don't run on your development machine. For "windows", you need to
                            run in Windows, and it will build and test for all versions of
                            Python. Default: auto.
                        ''')

    parser.add_argument('--archs',
                        default=None,
                        help='''
                            Comma-separated list of CPU architectures to build for.
                            When set to 'auto', builds the architectures natively supported
                            on this machine. Set this option to build an architecture
                            via emulation, for example, using binfmt_misc and QEMU.
                            Default: auto.
                            Choices: auto, auto64, auto32, native, all, {}
                        '''.format(", ".join(a.name for a in Architecture)))
    parser.add_argument('--output-dir',
                        default=os.environ.get('CIBW_OUTPUT_DIR', 'wheelhouse'),
                        help='Destination folder for the wheels.')
    parser.add_argument('package_dir',
                        default='.',
                        nargs='?',
                        help='''
                            Path to the package that you want wheels for. Must be a subdirectory of
                            the working directory. When set, the working directory is still
                            considered the 'project' and is copied into the Docker container on
                            Linux. Default: the working directory.
                        ''')

    parser.add_argument('--print-build-identifiers',
                        action='store_true',
                        help='Print the build identifiers matched by the current invocation and exit.')
    parser.add_argument('--allow-empty',
                        action='store_true',
                        help='Do not report an error code if the build does not match any wheels.')

    args = parser.parse_args()

    detect_obsolete_options()

    if args.platform != 'auto':
        platform = args.platform
    else:
        ci_provider = detect_ci_provider()
        if ci_provider is None:
            print(textwrap.dedent('''
                cibuildwheel: Unable to detect platform. cibuildwheel should run on your CI server;
                Travis CI, AppVeyor, Azure Pipelines, GitHub Actions, CircleCI, and Gitlab are
                supported. You can run on your development machine or other CI providers using the
                --platform argument. Check --help output for more information.
            '''), file=sys.stderr)
            sys.exit(2)
        if sys.platform.startswith('linux'):
            platform = 'linux'
        elif sys.platform == 'darwin':
            platform = 'macos'
        elif sys.platform == 'win32':
            platform = 'windows'
        else:
            print('cibuildwheel: Unable to detect platform from "sys.platform" in a CI environment. You can run '
                  'cibuildwheel using the --platform argument. Check --help output for more information.',
                  file=sys.stderr)
            sys.exit(2)

    if platform not in PLATFORMS:
        print(f'cibuildwheel: Unsupported platform: {platform}', file=sys.stderr)
        sys.exit(2)

    package_dir = Path(args.package_dir)
    output_dir = Path(args.output_dir)

    if platform == 'linux':
        repair_command_default = 'auditwheel repair -w {dest_dir} {wheel}'
    elif platform == 'macos':
        repair_command_default = 'delocate-listdeps {wheel} && delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}'
    elif platform == 'windows':
        repair_command_default = ''
    else:
        assert_never(platform)

    build_config = os.environ.get('CIBW_BUILD') or '*'
    skip_config = os.environ.get('CIBW_SKIP', '')
    test_skip = os.environ.get('CIBW_TEST_SKIP', '')
    environment_config = get_option_from_environment('CIBW_ENVIRONMENT', platform=platform, default='')
    before_all = get_option_from_environment('CIBW_BEFORE_ALL', platform=platform, default='')
    before_build = get_option_from_environment('CIBW_BEFORE_BUILD', platform=platform)
    repair_command = get_option_from_environment('CIBW_REPAIR_WHEEL_COMMAND', platform=platform, default=repair_command_default)
    dependency_versions = get_option_from_environment('CIBW_DEPENDENCY_VERSIONS', platform=platform, default='pinned')
    test_command = get_option_from_environment('CIBW_TEST_COMMAND', platform=platform)
    before_test = get_option_from_environment('CIBW_BEFORE_TEST', platform=platform)
    test_requires = get_option_from_environment('CIBW_TEST_REQUIRES', platform=platform, default='').split()
    test_extras = get_option_from_environment('CIBW_TEST_EXTRAS', platform=platform, default='')
    build_verbosity_str = get_option_from_environment('CIBW_BUILD_VERBOSITY', platform=platform, default='')

    package_files = {'setup.py', 'setup.cfg', 'pyproject.toml'}

    if not any(package_dir.joinpath(name).exists() for name in package_files):
        names = ', '.join(sorted(package_files, reverse=True))
        print(f'cibuildwheel: Could not find any of {{{names}}} at root of package', file=sys.stderr)
        sys.exit(2)

    # Passing this in as an environment variable will override pyproject.toml, setup.cfg, or setup.py
    requires_python_str: Optional[str] = os.environ.get('CIBW_PROJECT_REQUIRES_PYTHON') or get_requires_python_str(package_dir)
    requires_python = None if requires_python_str is None else SpecifierSet(requires_python_str)

    build_selector = BuildSelector(build_config=build_config, skip_config=skip_config, requires_python=requires_python)
    test_selector = TestSelector(skip_config=test_skip)

    try:
        environment = parse_environment(environment_config)
    except (EnvironmentParseError, ValueError):
        print(f'cibuildwheel: Malformed environment option "{environment_config}"', file=sys.stderr)
        traceback.print_exc(None, sys.stderr)
        sys.exit(2)

    if dependency_versions == 'pinned':
        dependency_constraints: Optional[DependencyConstraints] = DependencyConstraints.with_defaults()
    elif dependency_versions == 'latest':
        dependency_constraints = None
    else:
        dependency_versions_path = Path(dependency_versions)
        dependency_constraints = DependencyConstraints(dependency_versions_path)

    if test_extras:
        test_extras = f'[{test_extras}]'

    try:
        build_verbosity = min(3, max(-3, int(build_verbosity_str)))
    except ValueError:
        build_verbosity = 0

    # Add CIBUILDWHEEL environment variable
    # This needs to be passed on to the docker container in linux.py
    os.environ['CIBUILDWHEEL'] = '1'

    if args.archs is not None:
        archs_config_str = args.archs
    else:
        archs_config_str = get_option_from_environment('CIBW_ARCHS', platform=platform, default='auto')

    archs = Architecture.parse_config(archs_config_str, platform=platform)

    identifiers = get_build_identifiers(platform, build_selector, archs)

    if args.print_build_identifiers:
        for identifier in identifiers:
            print(identifier)
        sys.exit(0)

    manylinux_images: Optional[Dict[str, str]] = None
    if platform == 'linux':
        pinned_docker_images_file = resources_dir / 'pinned_docker_images.cfg'
        all_pinned_docker_images = ConfigParser()
        all_pinned_docker_images.read(pinned_docker_images_file)
        # all_pinned_docker_images looks like a dict of dicts, e.g.
        # { 'x86_64': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'i686': {'manylinux1': '...', 'manylinux2010': '...', 'manylinux2014': '...'},
        #   'pypy_x86_64': {'manylinux2010': '...' }
        #   ... }

        manylinux_images = {}

        for build_platform in ['x86_64', 'i686', 'pypy_x86_64', 'aarch64', 'ppc64le', 's390x']:
            pinned_images = all_pinned_docker_images[build_platform]

            config_name = f'CIBW_MANYLINUX_{build_platform.upper()}_IMAGE'
            config_value = os.environ.get(config_name)

            if config_value is None:
                # default to manylinux2010 if it's available, otherwise manylinux2014
                image = pinned_images.get('manylinux2010') or pinned_images.get('manylinux2014')
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
        manylinux_images=manylinux_images,
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
        print(f'cibuildwheel: No build identifiers selected: {build_selector}', file=sys.stderr)
        if not args.allow_empty:
            sys.exit(3)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    with cibuildwheel.util.print_new_wheels("\n{n} wheels produced in {m:.0f} minutes:", output_dir):
        if platform == 'linux':
            cibuildwheel.linux.build(build_options)
        elif platform == 'windows':
            cibuildwheel.windows.build(build_options)
        elif platform == 'macos':
            cibuildwheel.macos.build(build_options)
        else:
            assert_never(platform)


def detect_obsolete_options() -> None:
    # Check the old 'MANYLINUX1_*_IMAGE' options
    for (deprecated, alternative) in [('CIBW_MANYLINUX1_X86_64_IMAGE', 'CIBW_MANYLINUX_X86_64_IMAGE'),
                                      ('CIBW_MANYLINUX1_I686_IMAGE', 'CIBW_MANYLINUX_I686_IMAGE')]:
        if deprecated in os.environ:
            print(f"'{deprecated}' has been deprecated, and will be removed in a future release. Use the option '{alternative}' instead.")
            if alternative not in os.environ:
                print(f"Using value of option '{deprecated}' as replacement for '{alternative}'")
                os.environ[alternative] = os.environ[deprecated]
            else:
                print(f"Option '{alternative}' is not empty. Please unset '{deprecated}'")
                sys.exit(2)

    # Check for deprecated identifiers in 'CIBW_BUILD' and 'CIBW_SKIP' options
    for option in ['CIBW_BUILD', 'CIBW_SKIP']:
        for deprecated, alternative in [('manylinux1', 'manylinux'),
                                        ('macosx_10_6_intel', 'macosx_x86_64'),
                                        ('macosx_10_9_x86_64', 'macosx_x86_64')]:
            if option in os.environ and deprecated in os.environ[option]:
                print(f"Build identifiers with '{deprecated}' have been deprecated. Replacing all occurences of '{deprecated}' with '{alternative}' in the option '{option}'")
                os.environ[option] = os.environ[option].replace(deprecated, alternative)


def print_preamble(platform: str, build_options: BuildOptions) -> None:
    print(textwrap.dedent('''
             _ _       _ _   _       _           _
         ___|_| |_ _ _|_| |_| |_ _ _| |_ ___ ___| |
        |  _| | . | | | | | . | | | |   | -_| -_| |
        |___|_|___|___|_|_|___|_____|_|_|___|___|_|
        '''))

    print(f'cibuildwheel version {cibuildwheel.__version__}\n')

    print('Build options:')
    print(f'  platform: {platform!r}')
    for option, value in sorted(build_options._asdict().items()):
        print(f'  {option}: {value!r}')

    warnings = detect_warnings(platform, build_options)
    if warnings:
        print('\nWarnings:')
        for warning in warnings:
            print('  ' + warning)

    print('\nHere we go!\n')


def get_build_identifiers(
    platform: PlatformName, build_selector: BuildSelector, architectures: Set[Architecture]
) -> List[str]:
    python_configurations: Union[List[cibuildwheel.linux.PythonConfiguration],
                                 List[cibuildwheel.windows.PythonConfiguration],
                                 List[cibuildwheel.macos.PythonConfiguration]]

    if platform == 'linux':
        python_configurations = cibuildwheel.linux.get_python_configurations(build_selector, architectures)
    elif platform == 'windows':
        python_configurations = cibuildwheel.windows.get_python_configurations(build_selector, architectures)
    elif platform == 'macos':
        python_configurations = cibuildwheel.macos.get_python_configurations(build_selector, architectures)
    else:
        assert_never(platform)

    return [config.identifier for config in python_configurations]


def detect_warnings(platform: str, build_options: BuildOptions) -> List[str]:
    warnings = []

    # warn about deprecated {python} and {pip}
    for option_name in ['test_command', 'before_build']:
        option_value = getattr(build_options, option_name)

        if option_value:
            if '{python}' in option_value or '{pip}' in option_value:
                warnings.append(option_name + ": '{python}' and '{pip}' are no longer needed, and will be removed in a future release. Simply use 'python' or 'pip' instead.")

    return warnings


if __name__ == '__main__':
    main()
