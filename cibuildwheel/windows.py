from __future__ import print_function
import os, tempfile, subprocess, sys, shutil
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
from collections import namedtuple
from glob import glob

from .util import prepare_command, get_build_verbosity_extra_flags


def build(project_dir, output_dir, test_command, test_requires, before_build, build_verbosity, build_selector, environment):
    if os.path.exists('C:\\hostedtoolcache'):

        # We can't hard-code the paths because on Azure, we don't know which
        # bugfix release of Python we are getting so we need to check which
        # ones exist. We just use the first one that is found since there should
        # only be one.

        def python_path(version, arch):
            major, minor = version.split('.')[:2]
            suffix = 'x86' if arch == '32' else 'x64'
            path = glob("C:\\hostedtoolcache\\windows\\Python\\" + version.replace('x', '*') + "\\" + suffix)[0]
            return path

        def shell(args, env=None, cwd=None):
            print('+ ' + ' '.join(args))
            args = ['cmd', '/E:ON', '/V:ON', '/C'] + args
            return subprocess.check_call(' '.join(args), env=env, cwd=cwd)
    else:

        def python_path(version, arch):
            major, minor = version.split('.')[:2]
            path = 'C:\\Python' + major + minor
            if arch == '64':
                path += '-x64'
            return path

        run_with_env = os.path.join(os.path.dirname(__file__), 'resources', 'appveyor_run_with_env.cmd')
    
        # run_with_env is a cmd file that sets the right environment variables to

        def shell(args, env=None, cwd=None):
            # print the command executing for the logs
            print('+ ' + ' '.join(args))
            args = ['cmd', '/E:ON', '/V:ON', '/C', run_with_env] + args
            return subprocess.check_call(' '.join(args), env=env, cwd=cwd)

    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'arch', 'identifier', 'path'])

    # At this point, we need to check if we are running on Azure, because if
    # so Python is not located in the usual place. We recognize Azure by
    # checking for a C:\hostedtoolcache directory - there aren't any nice
    # environment variables we can use as on some other CI frameworks.


    python_configurations = [
        PythonConfiguration(version='2.7.x', arch="32", identifier='cp27-win32', path=python_path('2.7.x', '32')),
        PythonConfiguration(version='2.7.x', arch="64", identifier='cp27-win_amd64', path=python_path('2.7.x', '64')),
        PythonConfiguration(version='3.4.x', arch="32", identifier='cp34-win32', path=python_path('3.4.x', '32')),
        PythonConfiguration(version='3.4.x', arch="64", identifier='cp34-win_amd64', path=python_path('3.4.x', '64')),
        PythonConfiguration(version='3.5.x', arch="32", identifier='cp35-win32', path=python_path('3.5.x', '32')),
        PythonConfiguration(version='3.5.x', arch="64", identifier='cp35-win_amd64', path=python_path('3.5.x', '64')),
        PythonConfiguration(version='3.6.x', arch="32", identifier='cp36-win32', path=python_path('3.6.x', '32')),
        PythonConfiguration(version='3.6.x', arch="64", identifier='cp36-win_amd64', path=python_path('3.6.x', '64')),
        PythonConfiguration(version='3.7.x', arch="32", identifier='cp37-win32', path=python_path('3.7.x', '32')),
        PythonConfiguration(version='3.7.x', arch="64", identifier='cp37-win_amd64', path=python_path('3.7.x', '64')),
    ]

    abs_project_dir = os.path.abspath(project_dir)
    temp_dir = tempfile.mkdtemp(prefix='cibuildwheel')
    built_wheel_dir = os.path.join(temp_dir, 'built_wheel')

    for config in python_configurations:
        if not build_selector(config.identifier):
            print('cibuildwheel: Skipping build %s' % config.identifier, file=sys.stderr)
            continue

        # check python & pip exist for this configuration
        assert os.path.exists(os.path.join(config.path, 'python.exe'))
        assert os.path.exists(os.path.join(config.path, 'Scripts', 'pip.exe'))

        # setup dirs
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)

        env = os.environ.copy()
        # set up environment variables for run_with_env
        env['PYTHON_VERSION'] = config.version
        env['PYTHON_ARCH'] = config.arch
        env['PATH'] = os.pathsep.join([
            config.path,
            os.path.join(config.path, 'Scripts'),
            env['PATH']
        ])
        env = environment.as_dictionary(prev_environment=env)

        # for the logs - check we're running the right version of python
        shell(['python', '--version'], env=env)
        shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)\"'], env=env)

        # prepare the Python environment
        shell(['python', '-m', 'pip', 'install', '--upgrade', 'pip'],
              env=env)
        shell(['pip', 'install', '--upgrade', 'setuptools'], env=env)
        shell(['pip', 'install', 'wheel'], env=env)

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, project=abs_project_dir)
            shell([before_build_prepared], env=env)

        # build the wheel
        shell(['pip', 'wheel', abs_project_dir, '-w', built_wheel_dir, '--no-deps'] + get_build_verbosity_extra_flags(build_verbosity), env=env)
        built_wheel = glob(built_wheel_dir+'/*.whl')[0]

        # install the wheel
        shell(['pip', 'install', built_wheel], env=env)

        # test the wheel
        if test_requires:
            shell(['pip', 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from c:\, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(test_command, project=abs_project_dir)
            shell([test_command_prepared], cwd='c:\\', env=env)

        # we're all done here; move it to output (remove if already exists)
        dst = os.path.join(output_dir, os.path.basename(built_wheel))
        if os.path.isfile(dst):
            os.remove(dst)
        shutil.move(built_wheel, dst)
