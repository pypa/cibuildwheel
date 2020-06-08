import os
import shutil
import subprocess
import sys
import tempfile
from glob import glob
from zipfile import ZipFile

from typing import Dict, List, Optional, NamedTuple

from .environment import ParsedEnvironment
from .util import (
    BuildOptions,
    BuildSelector,
    download,
    get_build_verbosity_extra_flags,
    get_pip_script,
    prepare_command,
)


IS_RUNNING_ON_AZURE = os.path.exists('C:\\hostedtoolcache')
IS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'


def shell(args: List[str], env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> int:
    print('+ ' + ' '.join(args))
    return subprocess.check_call(' '.join(args), env=env, cwd=cwd, shell=True)


def get_nuget_args(version: str, arch: str) -> List[str]:
    python_name = 'python' if version[0] == '3' else 'python2'
    if arch == '32':
        python_name = python_name + 'x86'
    return [python_name, '-Version', version, '-OutputDirectory', 'C:\\cibw\\python']


class PythonConfiguration(NamedTuple):
    version: str
    arch: str
    identifier: str
    url: Optional[str]


def get_python_configurations(build_selector: BuildSelector) -> List[PythonConfiguration]:
    python_configurations = [
        # CPython
        PythonConfiguration(version='2.7.18', arch='32', identifier='cp27-win32', url=None),
        PythonConfiguration(version='2.7.18', arch='64', identifier='cp27-win_amd64', url=None),
        PythonConfiguration(version='3.5.4', arch='32', identifier='cp35-win32', url=None),
        PythonConfiguration(version='3.5.4', arch='64', identifier='cp35-win_amd64', url=None),
        PythonConfiguration(version='3.6.8', arch='32', identifier='cp36-win32', url=None),
        PythonConfiguration(version='3.6.8', arch='64', identifier='cp36-win_amd64', url=None),
        PythonConfiguration(version='3.7.7', arch='32', identifier='cp37-win32', url=None),
        PythonConfiguration(version='3.7.7', arch='64', identifier='cp37-win_amd64', url=None),
        PythonConfiguration(version='3.8.3', arch='32', identifier='cp38-win32', url=None),
        PythonConfiguration(version='3.8.3', arch='64', identifier='cp38-win_amd64', url=None),
        # PyPy
        PythonConfiguration(version='2.7', arch='32', identifier='pp27-win32', url='https://downloads.python.org/pypy/pypy2.7-v7.3.1-win32.zip'),
        PythonConfiguration(version='3.6', arch='32', identifier='pp36-win32', url='https://downloads.python.org/pypy/pypy3.6-v7.3.1-win32.zip'),
    ]

    if IS_RUNNING_ON_TRAVIS:
        # cannot install VCForPython27.msi which is needed for compiling C software
        # try with (and similar): msiexec /i VCForPython27.msi ALLUSERS=1 ACCEPT=YES /passive
        python_configurations = [c for c in python_configurations if not c.version.startswith('2.7')]

    # skip builds as required
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]

    return python_configurations


def extract_zip(zip_src: str, dest: str) -> None:
    with ZipFile(zip_src) as zip:
        zip.extractall(dest)


def install_cpython(version: str, arch: str, nuget: str) -> str:
    nuget_args = get_nuget_args(version, arch)
    installation_path = os.path.join(nuget_args[-1], nuget_args[0] + '.' + version, 'tools')
    shell([nuget, 'install'] + nuget_args)
    return installation_path


def install_pypy(version: str, arch: str, url: str) -> str:
    assert arch == '32'
    # Inside the PyPy zip file is a directory with the same name
    zip_filename = url.rsplit('/', 1)[-1]
    installation_path = os.path.join('C:\\cibw', os.path.splitext(zip_filename)[0])
    if not os.path.exists(installation_path):
        pypy_zip = os.path.join('C:\\cibw', zip_filename)
        download(url, pypy_zip)
        # Extract to the parent directory because the zip file still contains a directory
        extract_zip(pypy_zip, os.path.dirname(installation_path))
        pypy_exe = 'pypy3.exe' if version[0] == '3' else 'pypy.exe'
        shell(['mklink', os.path.join(installation_path, 'python.exe'), os.path.join(installation_path, pypy_exe)])
    return installation_path


def setup_python(python_configuration: PythonConfiguration, dependency_constraint_flags: List[str], environment: ParsedEnvironment) -> Dict[str, str]:
    nuget = 'C:\\cibw\\nuget.exe'
    if not os.path.exists(nuget):
        download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)

    if python_configuration.identifier.startswith('cp'):
        installation_path = install_cpython(python_configuration.version, python_configuration.arch, nuget)
    elif python_configuration.identifier.startswith('pp'):
        assert python_configuration.url is not None
        installation_path = install_pypy(python_configuration.version, python_configuration.arch, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")

    assert os.path.exists(os.path.join(installation_path, 'python.exe'))

    # set up PATH and environment variables for run_with_env
    env = os.environ.copy()
    env['PYTHON_VERSION'] = python_configuration.version
    env['PYTHON_ARCH'] = python_configuration.arch
    env['PATH'] = os.pathsep.join([
        installation_path,
        os.path.join(installation_path, 'Scripts'),
        env['PATH']
    ])
    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # for the logs - check we're running the right version of python
    shell(['where', 'python'], env=env)
    shell(['python', '--version'], env=env)
    shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)"'], env=env)
    where_python = subprocess.check_output(['where', 'python'], env=env, universal_newlines=True).splitlines()[0].strip()
    if where_python != os.path.join(installation_path, 'python.exe'):
        print("cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.", file=sys.stderr)
        exit(1)

    # make sure pip is installed
    if not os.path.exists(os.path.join(installation_path, 'Scripts', 'pip.exe')):
        shell(['python', get_pip_script] + dependency_constraint_flags, env=env, cwd="C:\\cibw")
    assert os.path.exists(os.path.join(installation_path, 'Scripts', 'pip.exe'))
    where_pip = subprocess.check_output(['where', 'pip'], env=env, universal_newlines=True).splitlines()[0].strip()
    if where_pip.strip() != os.path.join(installation_path, 'Scripts', 'pip.exe'):
        print("cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.", file=sys.stderr)
        exit(1)

    # prepare the Python environment
    shell(['python', '-m', 'pip', 'install', '--upgrade', 'pip'] + dependency_constraint_flags, env=env)
    shell(['pip', '--version'], env=env)
    shell(['pip', 'install', '--upgrade', 'setuptools', 'wheel'] + dependency_constraint_flags, env=env)

    return env


def build(options: BuildOptions) -> None:
    temp_dir = tempfile.mkdtemp(prefix='cibuildwheel')
    built_wheel_dir = os.path.join(temp_dir, 'built_wheel')
    repaired_wheel_dir = os.path.join(temp_dir, 'repaired_wheel')

    # install nuget as best way to provide python
    nuget = 'C:\\cibw\\nuget.exe'
    download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)

    python_configurations = get_python_configurations(options.build_selector)
    for config in python_configurations:
        dependency_constraint_flags = []
        if options.dependency_constraints:
            dependency_constraint_flags = [
                '-c', options.dependency_constraints.get_for_python_version(config.version)
            ]

        # install Python
        env = setup_python(config, dependency_constraint_flags, options.environment)

        # run the before_build command
        if options.before_build:
            before_build_prepared = prepare_command(options.before_build, project='.', package=options.package_dir)
            shell([before_build_prepared], env=env)

        # build the wheel
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)
        # os.path.abspath is need. Without it pip wheel may try to fetch package from pypi.org
        # see https://github.com/joerick/cibuildwheel/pull/369
        shell(['pip', 'wheel', os.path.abspath(options.package_dir), '-w', built_wheel_dir, '--no-deps'] + get_build_verbosity_extra_flags(options.build_verbosity), env=env)
        built_wheel = glob(os.path.join(built_wheel_dir, '*.whl'))[0]

        # repair the wheel
        if os.path.exists(repaired_wheel_dir):
            shutil.rmtree(repaired_wheel_dir)
        os.makedirs(repaired_wheel_dir)
        if built_wheel.endswith('none-any.whl') or not options.repair_command:
            # pure Python wheel or empty repair command
            shutil.move(built_wheel, repaired_wheel_dir)
        else:
            repair_command_prepared = prepare_command(options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir)
            shell([repair_command_prepared], env=env)
        repaired_wheel = glob(os.path.join(repaired_wheel_dir, '*.whl'))[0]

        if options.test_command:
            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            shell(['pip', 'install', 'virtualenv'] + dependency_constraint_flags, env=env)
            venv_dir = tempfile.mkdtemp()

            # Use --no-download to ensure determinism by using seed libraries
            # built into virtualenv
            shell(['python', '-m', 'virtualenv', '--no-download', venv_dir], env=env)

            virtualenv_env = env.copy()

            venv_script_path = os.path.join(venv_dir, 'Scripts')
            virtualenv_env['PATH'] = os.pathsep.join([
                venv_script_path,
                virtualenv_env['PATH'],
            ])
            virtualenv_env["__CIBW_VIRTUALENV_PATH__"] = venv_dir

            # check that we are using the Python from the virtual environment
            shell(['which', 'python'], env=virtualenv_env)

            if options.before_test:
                before_test_prepared = prepare_command(
                    options.before_test,
                    project='.',
                    package=options.package_dir
                )
                shell([before_test_prepared], env=virtualenv_env)

            # install the wheel
            shell(['pip', 'install', repaired_wheel + options.test_extras], env=virtualenv_env)

            # test the wheel
            if options.test_requires:
                shell(['pip', 'install'] + options.test_requires, env=virtualenv_env)

            # run the tests from c:\, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(
                options.test_command,
                project=os.path.abspath('.'),
                package=os.path.abspath(options.package_dir)
            )
            shell([test_command_prepared], cwd='c:\\', env=virtualenv_env)

            # clean up
            shutil.rmtree(venv_dir)

        # we're all done here; move it to output (remove if already exists)
        dst = os.path.join(options.output_dir, os.path.basename(repaired_wheel))
        if os.path.isfile(dst):
            os.remove(dst)
        shutil.move(repaired_wheel, dst)
