from __future__ import print_function
import os, tempfile, subprocess, shutil, sys
from time import sleep
from collections import namedtuple
from glob import glob

try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from .util import prepare_command, get_build_verbosity_extra_flags


IS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')
IS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'


def get_python_path(config):
    nuget_args = get_nuget_args(config)
    return os.path.join(nuget_args[-1], nuget_args[0] + "." + config.version, "tools")


def get_nuget_args(configuration):
    python_name = "python" if configuration.version[0] == '3' else "python2"
    if configuration.arch == "32":
        python_name = python_name + "x86"
    return [python_name, "-Version", configuration.version, "-OutputDirectory", "C:/cibw/python"]

def get_python_configurations(build_selector):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'arch', 'identifier'])
    python_configurations = [
        PythonConfiguration(version='2.7.17', arch="32", identifier='cp27-win32'),
        PythonConfiguration(version='2.7.17', arch="64", identifier='cp27-win_amd64'),
        PythonConfiguration(version='3.5.4', arch="32", identifier='cp35-win32'),
        PythonConfiguration(version='3.5.4', arch="64", identifier='cp35-win_amd64'),
        PythonConfiguration(version='3.6.8', arch="32", identifier='cp36-win32'),
        PythonConfiguration(version='3.6.8', arch="64", identifier='cp36-win_amd64'),
        PythonConfiguration(version='3.7.6', arch="32", identifier='cp37-win32'),
        PythonConfiguration(version='3.7.6', arch="64", identifier='cp37-win_amd64'),
        PythonConfiguration(version='3.8.1', arch="32", identifier='cp38-win32'),
        PythonConfiguration(version='3.8.1', arch="64", identifier='cp38-win_amd64'),
    ]

    if IS_RUNNING_ON_TRAVIS:
        # cannot install VCForPython27.msi which is needed for compiling C software
        # try with (and similar): msiexec /i VCForPython27.msi ALLUSERS=1 ACCEPT=YES /passive
        python_configurations = [c for c in python_configurations if not c.version.startswith('2.7.')]

     # skip builds as required
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]

    return python_configurations


def build(project_dir, output_dir, test_command, test_requires, test_extras, before_build, build_verbosity, build_selector, repair_command, environment, pip_version=None):
    def simple_shell(args, env=None, cwd=None):
        print('+ ' + ' '.join(args))
        args = ['cmd', '/E:ON', '/V:ON', '/C'] + args
        return subprocess.check_call(' '.join(args), env=env, cwd=cwd)

    def download(url, dest):
        print('+ Download ' + url + ' to ' + dest)
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        repeat_num = 3
        for i in range(repeat_num):
            try:
                response = urlopen(url)
            except:
                if i == repeat_num - 1:
                    raise
                sleep(3)
                continue
            break

        try:
            with open(dest, 'wb') as file:
                file.write(response.read())
        finally:
            response.close()

    if IS_RUNNING_ON_AZURE or IS_RUNNING_ON_TRAVIS:
        shell = simple_shell
    else:
        run_with_env = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources', 'appveyor_run_with_env.cmd'))

        # run_with_env is a cmd file that sets the right environment variables
        # to build on AppVeyor.
        def shell(args, env=None, cwd=None):
            # print the command executing for the logs
            print('+ ' + ' '.join(args))
            args = ['cmd', '/E:ON', '/V:ON', '/C', run_with_env] + args
            return subprocess.check_call(' '.join(args), env=env, cwd=cwd)

    abs_project_dir = os.path.abspath(project_dir)
    temp_dir = tempfile.mkdtemp(prefix='cibuildwheel')
    built_wheel_dir = os.path.join(temp_dir, 'built_wheel')
    repaired_wheel_dir = os.path.join(temp_dir, 'repaired_wheel')

    # install nuget as best way to provide python
    nuget = 'C:\\cibw\\nuget.exe'
    download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)
    # get pip fo this installation which not have.
    get_pip_script = 'C:\\cibw\\get-pip.py'
    download('https://bootstrap.pypa.io/get-pip.py', get_pip_script)

    python_configurations = get_python_configurations(build_selector)
    for config in python_configurations:
        # install Python
        config_python_path = get_python_path(config)
        simple_shell([nuget, "install"] + get_nuget_args(config))
        assert os.path.exists(os.path.join(config_python_path, 'python.exe'))

        # set up PATH and environment variables for run_with_env
        env = os.environ.copy()
        env['PYTHON_VERSION'] = config.version
        env['PYTHON_ARCH'] = config.arch
        env['PATH'] = os.pathsep.join([
            config_python_path,
            os.path.join(config_python_path, 'Scripts'),
            env['PATH']
        ])
        # update env with results from CIBW_ENVIRONMENT
        env = environment.as_dictionary(prev_environment=env)

        # for the logs - check we're running the right version of python
        simple_shell(['where', 'python'], env=env)
        simple_shell(['python', '--version'], env=env)
        simple_shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)\"'], env=env)

        # make sure pip is installed
        if not os.path.exists(os.path.join(config_python_path, 'Scripts', 'pip.exe')):
            simple_shell(['python', get_pip_script], env=env, cwd="C:\\cibw")
        assert os.path.exists(os.path.join(config_python_path, 'Scripts', 'pip.exe'))

        # prepare the Python environment
        if pip_version is not None:
            pip_str = 'pip==' + pip_version
        else:
            pip_str = 'pip'
        simple_shell(['python', '-m', 'pip', 'install', '--upgrade', pip_str], env=env)
        simple_shell(['pip', '--version'], env=env)
        simple_shell(['pip', 'install', '--upgrade', 'setuptools', 'wheel'], env=env)

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, project=abs_project_dir)
            shell([before_build_prepared], env=env)

        # build the wheel
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)
        shell(['pip', 'wheel', abs_project_dir, '-w', built_wheel_dir, '--no-deps'] + get_build_verbosity_extra_flags(build_verbosity), env=env)
        built_wheel = glob(os.path.join(built_wheel_dir, '*.whl'))[0]

        # repair the wheel
        if os.path.exists(repaired_wheel_dir):
            shutil.rmtree(repaired_wheel_dir)
        os.makedirs(repaired_wheel_dir)
        if built_wheel.endswith('none-any.whl') or not repair_command:
            # pure Python wheel or empty repair command
            shutil.move(built_wheel, repaired_wheel_dir)
        else:
            repair_command_prepared = prepare_command(repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir)
            shell([repair_command_prepared], env=env)
        repaired_wheel = glob(os.path.join(repaired_wheel_dir, '*.whl'))[0]

        if test_command:
            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            shell(['pip', 'install', 'virtualenv'], env=env)
            venv_dir = tempfile.mkdtemp()
            shell(['python', '-m', 'virtualenv', venv_dir], env=env)

            virtualenv_env = env.copy()
            virtualenv_env['PATH'] = os.pathsep.join([
                os.path.join(venv_dir, 'Scripts'),
                virtualenv_env['PATH'],
            ])

            # check that we are using the Python from the virtual environment
            shell(['which', 'python'], env=virtualenv_env)

            # install the wheel
            shell(['pip', 'install', repaired_wheel + test_extras], env=virtualenv_env)

            # test the wheel
            if test_requires:
                shell(['pip', 'install'] + test_requires, env=virtualenv_env)

            # run the tests from c:\, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(test_command, project=abs_project_dir)
            shell([test_command_prepared], cwd='c:\\', env=virtualenv_env)

            # clean up
            shutil.rmtree(venv_dir)

        # we're all done here; move it to output (remove if already exists)
        dst = os.path.join(output_dir, os.path.basename(repaired_wheel))
        if os.path.isfile(dst):
            os.remove(dst)
        shutil.move(repaired_wheel, dst)
