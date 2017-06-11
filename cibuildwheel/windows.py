from __future__ import print_function
import os, tempfile, subprocess, sys
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
from collections import namedtuple

from .util import prepare_command


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, skip):
    # run_with_env is a cmd file that sets the right environment variables to
    run_with_env = os.path.join(tempfile.gettempdir(), 'appveyor_run_with_env.cmd')
    if not os.path.exists(run_with_env):
        with open(run_with_env, 'wb') as f:
            request = urlopen('https://github.com/ogrisel/python-appveyor-demo/raw/09a1c8672e5015a74d8f69d07add6ee803c176ec/appveyor/run_with_env.cmd')
            f.write(request.read())

    def shell(args, env=None, cwd=None):
        # print the command executing for the logs
        print('+ ' + ' '.join(args))
        args = ['cmd', '/E:ON', '/V:ON', '/C', run_with_env] + args
        return subprocess.check_call(' '.join(args), env=env, cwd=cwd)

    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'arch', 'identifier', 'path'])
    python_configurations = [
        PythonConfiguration(version='2.7.x', arch="32", identifier='cp27-win32', path='C:\Python27'),
        PythonConfiguration(version='2.7.x', arch="64", identifier='cp27-win_amd64', path='C:\Python27-x64'),
        PythonConfiguration(version='3.3.x', arch="32", identifier='cp33-win32', path='C:\Python33'),
        PythonConfiguration(version='3.3.x', arch="64", identifier='cp33-win_amd64', path='C:\Python33-x64'),
        PythonConfiguration(version='3.4.x', arch="32", identifier='cp34-win32', path='C:\Python34'),
        PythonConfiguration(version='3.4.x', arch="64", identifier='cp34-win_amd64', path='C:\Python34-x64'),
        PythonConfiguration(version='3.5.x', arch="32", identifier='cp35-win32', path='C:\Python35'),
        PythonConfiguration(version='3.5.x', arch="64", identifier='cp35-win_amd64', path='C:\Python35-x64'),
        PythonConfiguration(version='3.6.x', arch="32", identifier='cp36-win32', path='C:\Python36'),
        PythonConfiguration(version='3.6.x', arch="64", identifier='cp36-win_amd64', path='C:\Python36-x64'),
    ]

    for config in python_configurations:
        if skip(config.identifier):
            print('cibuildwheel: Skipping build %s' % config.identifier, file=sys.stderr)
            continue

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
        shell(['pip', 'install', '--disable-pip-version-check', '--user', '--upgrade', 'pip'],
              env=env)
        shell(['pip', 'install', 'wheel'], env=env)

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, python='python', pip='pip')
            shell([before_build_prepared], env=env)

        # install the package first to take care of dependencies
        shell(['pip', 'install', project_dir], env=env)

        # build the wheel
        shell(['pip', 'wheel', project_dir, '-w', output_dir, '--no-deps'], env=env)

        # install the wheel
        shell(['pip', 'install', package_name, '--upgrade',
               '--force-reinstall', '--no-deps', '--no-index', '-f',
               output_dir], env=env)

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
