from __future__ import print_function
import os, tempfile, subprocess, sys, shutil
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
from collections import namedtuple
from glob import glob

from .util import prepare_command, get_build_verbosity_extra_flags


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, build_verbosity, build_selector, environment):
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
        PythonConfiguration(version='3.4.x', arch="32", identifier='cp34-win32', path='C:\Python34'),
        PythonConfiguration(version='3.4.x', arch="64", identifier='cp34-win_amd64', path='C:\Python34-x64'),
        PythonConfiguration(version='3.5.x', arch="32", identifier='cp35-win32', path='C:\Python35'),
        PythonConfiguration(version='3.5.x', arch="64", identifier='cp35-win_amd64', path='C:\Python35-x64'),
        PythonConfiguration(version='3.6.x', arch="32", identifier='cp36-win32', path='C:\Python36'),
        PythonConfiguration(version='3.6.x', arch="64", identifier='cp36-win_amd64', path='C:\Python36-x64'),
        PythonConfiguration(version='3.7.x', arch="32", identifier='cp37-win32', path='C:\Python37'),
        PythonConfiguration(version='3.7.x', arch="64", identifier='cp37-win_amd64', path='C:\Python37-x64'),
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
