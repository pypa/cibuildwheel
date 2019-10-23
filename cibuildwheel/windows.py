from __future__ import print_function
import os, tempfile, subprocess, shutil, sys
from collections import namedtuple
from glob import glob

try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

from .util import prepare_command, get_build_verbosity_extra_flags


IS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')
IS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'

def get_python_path(config):
    if IS_RUNNING_ON_AZURE:
        # We can't hard-code the paths because on Azure, we don't know which
        # bugfix release of Python we are getting so we need to check which
        # ones exist. We just use the first one that is found since there should
        # only be one.
        path_pattern = 'C:\\hostedtoolcache\\windows\\Python\\{version}\\{arch}'.format(
            version=config.version.replace('x', '*'),
            arch='x86' if config.arch == '32' else 'x64'
        )
        try:
            return glob(path_pattern)[0]
        except IndexError:
            raise Exception('Could not find a Python install at ' + path_pattern)
    elif IS_RUNNING_ON_TRAVIS:
        if config.version == "3.4.x":
            return config.path
        else:
            nuget_args = get_nuget_args(config)
            return os.path.join(nuget_args[-1], nuget_args[0] + "." + config.nuget_version, "tools")
    else:
        # Assume we're running on AppVeyor
        major, minor = config.version.split('.')[:2]
        return 'C:\\Python{major}{minor}{arch}'.format(
            major=major,
            minor=minor,
            arch = '-x64' if config.arch == '64' else ''
        )


def get_nuget_args(configuration):
    if configuration.nuget_version is None:
        return None
    python_name = "python" if configuration.version[0] == '3' else "python2"
    if configuration.arch == "32":
        python_name = python_name + "x86"
    return [python_name, "-Version", configuration.nuget_version, "-OutputDirectory", "C:/python"]

def get_python_configurations(build_selector):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'arch', 'identifier', 'path', "nuget_version"])
    python_configurations = [
        PythonConfiguration(version='2.7.x', arch="32", identifier='cp27-win32', path='C:\\Python27', nuget_version="2.7.16"),
        PythonConfiguration(version='2.7.x', arch="64", identifier='cp27-win_amd64', path='C:\\Python27-x64', nuget_version="2.7.16"),
        PythonConfiguration(version='3.4.x', arch="32", identifier='cp34-win32', path='C:\\Python34', nuget_version=None),
        PythonConfiguration(version='3.4.x', arch="64", identifier='cp34-win_amd64', path='C:\\Python34-x64', nuget_version=None),
        PythonConfiguration(version='3.5.x', arch="32", identifier='cp35-win32', path='C:\\Python35', nuget_version="3.5.4"),
        PythonConfiguration(version='3.5.x', arch="64", identifier='cp35-win_amd64', path='C:\\Python35-x64', nuget_version="3.5.4"),
        PythonConfiguration(version='3.6.x', arch="32", identifier='cp36-win32', path='C:\\Python36', nuget_version="3.6.8"),
        PythonConfiguration(version='3.6.x', arch="64", identifier='cp36-win_amd64', path='C:\\Python36-x64', nuget_version="3.6.8"),
        PythonConfiguration(version='3.7.x', arch="32", identifier='cp37-win32', path='C:\\Python37', nuget_version="3.7.4"),
        PythonConfiguration(version='3.7.x', arch="64", identifier='cp37-win_amd64', path='C:\\Python37-x64', nuget_version="3.7.4")
    ]

    if IS_RUNNING_ON_AZURE:
        # Python 3.4 isn't supported on Azure.
        # See https://github.com/Microsoft/azure-pipelines-tasks/issues/9674
        python_configurations = [c for c in python_configurations if c.version != '3.4.x']
    
    if IS_RUNNING_ON_TRAVIS:
        # cannot install VCForPython27.msi which is needed for compiling C software
        # try with (and similar): msiexec /i VCForPython27.msi ALLUSERS=1 ACCEPT=YES /passive
        # no easy and stable way fo installing python 3.4 
        python_configurations = [c for c in python_configurations if c.version != '2.7.x' and c.version != '3.4.x']

     # skip builds as required
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]
   
    return python_configurations



def build(project_dir, output_dir, test_command, test_requires, test_extras, before_build, build_verbosity, build_selector, environment):
    if IS_RUNNING_ON_AZURE or IS_RUNNING_ON_TRAVIS:
        def shell(args, env=None, cwd=None):
            print('+ ' + ' '.join(args))
            args = ['cmd', '/E:ON', '/V:ON', '/C'] + args
            return subprocess.check_call(' '.join(args), env=env, cwd=cwd)
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

    if IS_RUNNING_ON_TRAVIS:
        # instal nuget as best way for provide python
        shell(["choco", "install", "nuget.commandline"])
        # get pip fo this installation which not have. 
        get_pip_url = 'https://bootstrap.pypa.io/get-pip.py'
        get_pip_script = 'C:\\get-pip.py'
        shell(['curl', '-L', '-o', get_pip_script, get_pip_url])

    python_configurations = get_python_configurations(build_selector)
    for config in python_configurations:
        config_python_path = get_python_path(config)
        if IS_RUNNING_ON_TRAVIS and config.nuget_version is not None and not os.path.exists(config_python_path):
            shell(["nuget", "install"] + get_nuget_args(config))
            if not os.path.exists(os.path.join(config_python_path, 'Scripts', 'pip.exe')):
                shell([os.path.join(config_python_path, 'python.exe'), get_pip_script ])

        # check python & pip exist for this configuration
        assert os.path.exists(os.path.join(config_python_path, 'python.exe'))
        assert os.path.exists(os.path.join(config_python_path, 'Scripts', 'pip.exe'))

        # setup dirs
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)

        env = os.environ.copy()
        # set up environment variables for run_with_env
        env['PYTHON_VERSION'] = config.version
        env['PYTHON_ARCH'] = config.arch
        env['PATH'] = os.pathsep.join([
            config_python_path,
            os.path.join(config_python_path, 'Scripts'),
            env['PATH']
        ])
        env = environment.as_dictionary(prev_environment=env)

        # for the logs - check we're running the right version of python
        shell(['python', '--version'], env=env)
        shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)\"'], env=env)

        # prepare the Python environment
        if config.version == "3.4.x":
            shell(['python', '-m', 'pip', 'install', 'pip==19.1.1'],
              env=env)
        else:
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
            shell(['pip', 'install', built_wheel + test_extras], env=virtualenv_env)

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
        dst = os.path.join(output_dir, os.path.basename(built_wheel))
        if os.path.isfile(dst):
            os.remove(dst)
        shutil.move(built_wheel, dst)
