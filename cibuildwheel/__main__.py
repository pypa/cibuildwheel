import argparse
import os
import sys
import textwrap
import traceback
from configparser import ConfigParser
from pathlib import Path

from typing import Any, Dict, List, Optional, overload

import cibuildwheel
import cibuildwheel.linux
import cibuildwheel.macos
import cibuildwheel.windows
from cibuildwheel.environment import (
    EnvironmentParseError,
    parse_environment,
)
from cibuildwheel.util import (
    BuildOptions,
    BuildSelector,
    DependencyConstraints,
    Unbuffered,
    detect_ci_provider,
    resources_dir,
)


@overload
def get_option_from_environment(option_name: str, platform: Optional[str], default: str) -> str: ...  # noqa: E704
@overload
def get_option_from_environment(option_name: str, platform: Optional[str] = None, default: None = None) -> Optional[str]: ...  # noqa: E704 E302
def get_option_from_environment(option_name: str, platform: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:  # noqa: E302
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
    parser.add_argument('--use-binfmt',
                        default=False,
                        action='store_true',
                        help='''
                            Use QEMU Emulation to run the Docker images of other architectures.
                        ''')

    parser.add_argument('--print-build-identifiers',
                        action='store_true',
                        help='Print the build identifiers matched by the current invocation and exit.')

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
            exit(2)
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
            exit(2)

    package_dir = Path(args.package_dir)
    output_dir = Path(args.output_dir)

    if platform == 'linux':
        repair_command_default = 'auditwheel repair -w {dest_dir} {wheel}'
    elif platform == 'macos':
        repair_command_default = 'delocate-listdeps {wheel} && delocate-wheel --require-archs x86_64 -w {dest_dir} {wheel}'
    else:
        repair_command_default = ''

    build_config, skip_config = os.environ.get('CIBW_BUILD', '*'), os.environ.get('CIBW_SKIP', '')
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

    build_selector = BuildSelector(build_config, skip_config)

    try:
        environment = parse_environment(environment_config)
    except (EnvironmentParseError, ValueError):
        print(f'cibuildwheel: Malformed environment option "{environment_config}"', file=sys.stderr)
        traceback.print_exc(None, sys.stderr)
        exit(2)

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

    if not any((package_dir / name).exists()
               for name in ["setup.py", "setup.cfg", "pyproject.toml"]):
        print('cibuildwheel: Could not find setup.py, setup.cfg or pyproject.toml at root of package', file=sys.stderr)
        exit(2)

    # qemu is only available on linux platforms
    use_binfmt = args.use_binfmt and platform == 'linux'

    if args.print_build_identifiers:
        print_build_identifiers(platform, build_selector, use_binfmt)
        exit(0)

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
        repair_command=repair_command,
        environment=environment,
        dependency_constraints=dependency_constraints,
        manylinux_images=manylinux_images,
        use_binfmt=use_binfmt
    )

    # Python is buffering by default when running on the CI platforms, giving problems interleaving subprocess call output with unflushed calls to 'print'
    sys.stdout = Unbuffered(sys.stdout)  # type: ignore

    print_preamble(platform, build_options)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    if platform == 'linux':
        cibuildwheel.linux.build(build_options)
    elif platform == 'windows':
        cibuildwheel.windows.build(build_options)
    elif platform == 'macos':
        cibuildwheel.macos.build(build_options)
    else:
        print(f'cibuildwheel: Unsupported platform: {platform}', file=sys.stderr)
        exit(2)


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
                exit(2)

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


def print_build_identifiers(platform: str, build_selector: BuildSelector, use_binfmt: bool) -> None:
    python_configurations: List[Any] = []
    if platform == 'linux':
        python_configurations = cibuildwheel.linux.get_python_configurations(build_selector, use_binfmt)
    elif platform == 'windows':
        python_configurations = cibuildwheel.windows.get_python_configurations(build_selector)
    elif platform == 'macos':
        python_configurations = cibuildwheel.macos.get_python_configurations(build_selector)

    for config in python_configurations:
        print(config.identifier)


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
