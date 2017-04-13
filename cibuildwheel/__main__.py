from __future__ import print_function
import argparse, os, subprocess, sys, textwrap

import cibuildwheel
import cibuildwheel.linux, cibuildwheel.windows, cibuildwheel.macos
from cibuildwheel.util import BuildSkipper

def get_option_from_environment(option_name, platform=None):
    '''
    Returns an option from the environment, optionally scoped by the platform.

    Example:
      get_option_from_environment('CIBW_COLOR', platform='macos')

      This will return the value of CIBW_COLOR_MACOS if it exists, otherwise the value of
      CIBW_COLOR.
    '''
    if platform:
        option = os.environ.get('%s_%s' % (option_name, platform.upper()))
        if option is not None:
            return option

    return os.environ.get(option_name)


def main():
    parser = argparse.ArgumentParser(
        description='Build wheels for all the platforms.',
        epilog=('Most options are supplied via environment variables. '
                'See https://github.com/joerick/cibuildwheel#options for info.'))

    parser.add_argument('--platform',
                        choices=['auto', 'linux', 'macos', 'windows'],
                        default=os.environ.get('CIBW_PLATFORM', 'auto'),
                        help=('Platform to build for. For "linux" you need docker running, on Mac '
                              'or Linux. For "macos", you need a Mac machine, and note that this '
                              'script is going to automatically install MacPython on your system, '
                              'so don\'t run on your development machine. For "windows", you need to '
                              'run in Windows, and it will build and test for all versions of '
                              'Python at C:\\PythonXX[-x64]. Default: auto.'))
    parser.add_argument('--output-dir',
                        default=os.environ.get('CIBW_OUTPUT_DIR', 'wheelhouse'),
                        help='Destination folder for the wheels.')
    parser.add_argument('project_dir',
                        default='.',
                        nargs='?',
                        help=('Path to the project that you want wheels for. Default: the current '
                              'directory.'))

    args = parser.parse_args()

    if args.platform != 'auto':
        platform = args.platform
    else:
        if os.environ.get('TRAVIS_OS_NAME') == 'linux':
            platform = 'linux'
        elif os.environ.get('TRAVIS_OS_NAME') == 'osx':
            platform = 'macos'
        elif 'APPVEYOR' in os.environ:
            platform = 'windows'
        else:
            print('Unable to detect platform. cibuildwheel should run on your CI server, '
                  'Travis CI and Appveyor are supported. You can run on your development '
                  'machine using the --platform argument. Check --help output for more '
                  'information.',
                  file=sys.stderr)
            exit(2)

    output_dir = args.output_dir
    test_command = os.environ.get('CIBW_TEST_COMMAND', None)
    test_requires = os.environ.get('CIBW_TEST_REQUIRES', '').split()
    project_dir = args.project_dir
    before_build = get_option_from_environment('CIBW_BEFORE_BUILD', platform=platform)
    skip_config = os.environ.get('CIBW_SKIP', '')

    skip = BuildSkipper(skip_config)

    try:
        project_setup_py = os.path.join(project_dir, 'setup.py')
        name_output = subprocess.check_output([sys.executable, project_setup_py, '--name'])
        # the last line of output is the name
        package_name = name_output.strip().splitlines()[-1]
    except subprocess.CalledProcessError as err:
        if not os.path.exists(project_setup_py):
            print('cibuildwheel: Could not find setup.py at root of project', file=sys.stderr)
            exit(2)
        else:
            print('cibuildwheel: Failed to get name of the package. Command was %s' % err.cmd,
                  file=sys.stderr)
            exit(2)

    if package_name == '' or package_name == 'UNKNOWN':
        print('cibuildwheel: Invalid package name "%s". Check your setup.py' % package_name,
              file=sys.stderr)
        exit(2)

    build_options = dict(
        project_dir=project_dir,
        package_name=package_name,
        output_dir=output_dir,
        test_command=test_command,
        test_requires=test_requires,
        before_build=before_build,
        skip=skip,
    )

    print_preamble(platform, build_options)

    if platform == 'linux':
        cibuildwheel.linux.build(**build_options)
    elif platform == 'windows':
        cibuildwheel.windows.build(**build_options)
    elif platform == 'macos':
        cibuildwheel.macos.build(**build_options)
    else:
        raise Exception('Unsupported platform')

def print_preamble(platform, build_options):
    print(textwrap.dedent('''
             _ _       _ _   _       _           _
         ___|_| |_ _ _|_| |_| |_ _ _| |_ ___ ___| |
        |  _| | . | | | | | . | | | |   | -_| -_| |
        |___|_|___|___|_|_|___|_____|_|_|___|___|_|
        '''))

    print('cibuildwheel version %s\n' % cibuildwheel.__version__)


    print('Build options:')
    print('  platform: %r' % platform)
    for option, value in build_options.items():
        print('  %s: %r' % (option, value))

    print('\nHere we go!\n')

if __name__ == '__main__':
    main()
