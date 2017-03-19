from __future__ import print_function
import argparse, os, subprocess, sys, tempfile, shlex
from collections import namedtuple
from glob import glob

try:
    # Python 3
    import urllib.request as urllib2
except ImportError:
    # Python 2
    import urllib2

try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote


def linux_build(project_dir, package_name, output_dir, test_command, test_requires):
    for docker_image in ['quay.io/pypa/manylinux1_x86_64', 'quay.io/pypa/manylinux1_i686']:
        bash_script = '''
            set -o errexit
            set -o xtrace
            cd /project

            for PYBIN in /opt/python/*/bin; do
                "$PYBIN/pip" wheel . -w /tmp/linux_wheels
            done

            for whl in /tmp/linux_wheels/*.whl; do
                auditwheel repair "$whl" -w /output
            done

            # Install packages and test
            for PYBIN in /opt/python/*/bin/; do
                # Install the wheel we just built
                "$PYBIN/pip" install {package_name} --no-index -f /output

                # Install any requirements to run the tests
                if [ ! -z "{test_requires}" ]; then
                    "$PYBIN/pip" install {test_requires}
                fi

                # Run the tests from a different directory
                if [ ! -z {test_command} ]; then
                    (cd "$HOME" && export PATH=$PYBIN:$PATH && sh -c {test_command})
                fi
            done
        '''.format(
            package_name=package_name,
            test_requires=' '.join(test_requires),
            test_command=shlex_quote(test_command.format(project='/project') if test_command else ''),
        )

        docker_process = subprocess.Popen([
                'docker',
                'run',
                '--rm',
                '-i',
                '-v', '%s:/project' % os.path.abspath(project_dir),
                '-v', '%s:/output' % os.path.abspath(output_dir),
                docker_image,
                '/bin/bash'],
            stdin=subprocess.PIPE)

        docker_process.communicate(bash_script)

        if docker_process.returncode != 0:
            exit(1)


def windows_build(project_dir, package_name, output_dir, test_command, test_requires):
    # run_with_env is a cmd file that sets the right environment variables to
    run_with_env = os.path.join(tempfile.gettempdir(), 'appveyor_run_with_env.cmd')
    if not os.path.exists(run_with_env):
        with open(run_with_env, 'wb') as f:
            request = urllib2.urlopen('https://github.com/ogrisel/python-appveyor-demo/raw/09a1c8672e5015a74d8f69d07add6ee803c176ec/appveyor/run_with_env.cmd')
            f.write(request.read())

    def shell(args, env=None, cwd=None):
        # print the command executing for the logs
        print('+ ' + ' '.join(args))
        args = ['cmd', '/E:ON', '/V:ON', '/C', run_with_env] + args
        return subprocess.check_call(' '.join(args), env=env, cwd=cwd)

    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'arch', 'path'])
    python_configurations = [
        PythonConfiguration(version='2.7.x', arch="32", path='C:\Python27'),
        PythonConfiguration(version='2.7.x', arch="64", path='C:\Python27-x64'),
        PythonConfiguration(version='3.3.x', arch="32", path='C:\Python33'),
        PythonConfiguration(version='3.3.x', arch="64", path='C:\Python33-x64'),
        PythonConfiguration(version='3.4.x', arch="32", path='C:\Python34'),
        PythonConfiguration(version='3.4.x', arch="64", path='C:\Python34-x64'),
        PythonConfiguration(version='3.5.x', arch="32", path='C:\Python35'),
        PythonConfiguration(version='3.5.x', arch="64", path='C:\Python35-x64'),
        PythonConfiguration(version='3.6.x', arch="32", path='C:\Python36'),
        PythonConfiguration(version='3.6.x', arch="64", path='C:\Python36-x64'),
    ]

    for config in python_configurations:
        env = os.environ.copy()
        # set up environment variables for run_with_env
        env['PYTHON_VERSION'] = config.version
        env['PYTHON_ARCH'] = config.arch
        env['PATH'] = os.pathsep.join([
            config.path,
            os.path.join(config.path, 'Scripts'),
            env['PATH']
        ])

        # for the logs - check we're running the right version of python
        shell(['python', '--version'], env=env)
        shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)\"'], env=env)

        # prepare the Python environment
        shell(['pip', 'install', '--disable-pip-version-check', '--user', '--upgrade', 'pip'], env=env)
        shell(['pip', 'install', 'wheel'], env=env)

        # build the wheel
        shell(['pip', 'wheel', project_dir, '-w', output_dir], env=env)

        # install the wheel
        shell(['pip', 'install', package_name, '--no-index', '-f', output_dir], env=env)

        # test the wheel
        if test_requires:
            shell(['pip', 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from c:\, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            abs_project_dir = os.path.abspath(project_dir)
            test_command_absolute = test_command.format(project=abs_project_dir)
            shell([test_command_absolute], cwd='c:\\', env=env)


def macos_build(project_dir, package_name, output_dir, test_command, test_requires):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', url='https://www.python.org/ftp/python/2.7.13/python-2.7.13-macosx10.6.pkg'),
        PythonConfiguration(version='3.4', url='https://www.python.org/ftp/python/3.4.4/python-3.4.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.5', url='https://www.python.org/ftp/python/3.5.3/python-3.5.3-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', url='https://www.python.org/ftp/python/3.6.0/python-3.6.0-macosx10.6.pkg'),
    ]

    def shell(args, env=None, cwd=None):
        # print the command executing for the logs
        print('+ ' + ' '.join(shlex_quote(a) for a in args))
        return subprocess.check_call(args, env=env, cwd=cwd)

    for config in python_configurations:
        # download the pkg
        shell(['curl', '-L', '-o', '/tmp/Python.pkg', config.url])
        # install
        shell(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])

        env = os.environ.copy()
        env['PATH'] = os.pathsep.join([
            '/Library/Frameworks/Python.framework/Versions/%s/bin' % config.version,
            env['PATH'],
        ])

        python = 'python3' if config.version[0] == '3' else 'python2'
        pip = 'pip3' if config.version[0] == '3' else 'pip2'

        # check what version we're on
        shell(['which', python], env=env)
        shell([python, '--version'], env=env)

        # install pip & wheel
        shell([python, '-m', 'ensurepip', '--upgrade'], env=env)
        shell(['which', pip], env=env)  # todo: remove
        shell([pip, '--version'])
        shell([pip, 'install', 'wheel'], env=env)
        shell([pip, 'install', 'delocate'], env=env)

        # build the wheel to temp dir
        temp_wheel_dir = '/tmp/tmpwheel%s' % config.version
        shell([pip, 'wheel', project_dir, '-w', temp_wheel_dir], env=env)
        temp_wheel = glob(temp_wheel_dir+'/*.whl')[0]

        # list the dependencies
        shell(['delocate-listdeps', temp_wheel], env=env)
        # rebuild the wheel with shared libraries included and place in output dir
        shell(['delocate-wheel', '-w', output_dir, temp_wheel], env=env)

        # install the wheel
        shell([pip, 'install', package_name, '--no-index', '--find-links', output_dir], env=env)

        # test the wheel
        if test_requires:
            shell([pip, '-v', 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            abs_project_dir = os.path.abspath(project_dir)
            test_command_absolute = test_command.format(project=abs_project_dir)
            shell(['which', 'nosetests'], env=env)  # todo: remove
            shell(['which', 'nosetests'], cwd=os.environ['HOME'], env=env)  # todo: remove
            shell(['nosetests', '-v'], env=env)  # todo: remove
            shell(['nosetests', '-v'], cwd=os.environ['HOME'], env=env)  # todo: remove
            shell(shlex.split(test_command_absolute), cwd=os.environ['HOME'], env=env)


def main():
    parser = argparse.ArgumentParser(
        description='Build wheels for all the platforms.',
        epilog=('Most options are supplied via environment variables. '
                'See https://github.com/joerick/cibuildwheel#options for info.'))

    parser.add_argument('--platform',
                        choices=['auto', 'linux', 'macos', 'windows'],
                        default='auto',
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

    output_dir = args.output_dir
    test_command = os.environ.get('CIBW_TEST_COMMAND', None)
    test_requires = os.environ.get('CIBW_TEST_REQUIRES', '').split()
    project_dir = args.project_dir

    try:
        project_setup_py = os.path.join(project_dir, 'setup.py')
        package_name = subprocess.check_output([sys.executable, project_setup_py, '--name'])
    except subprocess.CalledProcessError as err:
        if not os.path.exists(project_setup_py):
            print('cibuildwheel: Could not find setup.py at root of project', file=sys.stderr)
            exit(2)
        else:
            print('cibuildwheel: Failed to get name of the package. Command was %s' % err.cmd,
                  file=sys.stderr)
            exit(2)

    package_name = package_name.strip()

    if package_name == '' or package_name == 'UNKNOWN':
        print('cibuildwheel: Invalid package name "%s". Check your setup.py' % package_name, 
              file=sys.stderr)
        exit(2)

    build_args = dict(
        project_dir=project_dir,
        package_name=package_name,
        output_dir=output_dir,
        test_command=test_command,
        test_requires=test_requires
    )

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

    if platform == 'linux':
        linux_build(**build_args)
    elif platform == 'windows':
        windows_build(**build_args)
    elif platform == 'macos':
        macos_build(**build_args)
    else:
        print('cibuildwheel: Unsupported platform %s' % platform, file=sys.stderr)
        exit(1)

if __name__ == '__main__':
    main()
