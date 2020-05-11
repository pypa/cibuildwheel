import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
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


IS_RUNNING_ON_AZURE = Path('C:\\hostedtoolcache').exists()
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


def extract_zip(zip_src: Path, dest: Path) -> None:
    with ZipFile(zip_src) as zip:
        zip.extractall(dest)


def install_cpython(version: str, arch: str, nuget: Path) -> Path:
    nuget_args = get_nuget_args(version, arch)
    installation_path = Path(nuget_args[-1]) / (nuget_args[0] + '.' + version) / 'tools'
    shell([str(nuget), 'install'] + nuget_args)
    return installation_path


def install_pypy(version: str, arch: str, url: str) -> Path:
    assert arch == '32'
    # Inside the PyPy zip file is a directory with the same name
    zip_filename = url.rsplit('/', 1)[-1]
    extension = ".zip"
    assert zip_filename.endswith(extension)
    installation_path = Path('C:\\cibw') / zip_filename[:-len(extension)]
    if not installation_path.exists():
        pypy_zip = Path('C:\\cibw') / zip_filename
        download(url, pypy_zip)
        # Extract to the parent directory because the zip file still contains a directory
        extract_zip(pypy_zip, installation_path.parent)
        pypy_exe = 'pypy3.exe' if version[0] == '3' else 'pypy.exe'
        (installation_path / 'python.exe').symlink_to(installation_path / pypy_exe)
    return installation_path


def setup_python(python_configuration: PythonConfiguration, dependency_constraint_flags: List[str], environment: ParsedEnvironment) -> Dict[str, str]:
    nuget = Path('C:\\cibw\\nuget.exe')
    if not nuget.exists():
        download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)

    if python_configuration.identifier.startswith('cp'):
        installation_path = install_cpython(python_configuration.version, python_configuration.arch, nuget)
    elif python_configuration.identifier.startswith('pp'):
        assert python_configuration.url is not None
        installation_path = install_pypy(python_configuration.version, python_configuration.arch, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")

    assert (installation_path / 'python.exe').exists()

    # set up PATH and environment variables for run_with_env
    env = os.environ.copy()
    env['PYTHON_VERSION'] = python_configuration.version
    env['PYTHON_ARCH'] = python_configuration.arch
    env['PATH'] = os.pathsep.join([
        str(installation_path),
        str(installation_path / 'Scripts'),
        env['PATH']
    ])
    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # for the logs - check we're running the right version of python
    shell(['where', 'python'], env=env)
    shell(['python', '--version'], env=env)
    shell(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)"'], env=env)
    where_python = subprocess.check_output(['where', 'python'], env=env, universal_newlines=True).splitlines()[0].strip()
    if where_python != str(installation_path / 'python.exe'):
        print("cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.", file=sys.stderr)
        exit(1)

    # make sure pip is installed
    if not (installation_path / 'Scripts' / 'pip.exe').exists():
        shell(['python', str(get_pip_script)] + dependency_constraint_flags, env=env, cwd="C:\\cibw")
    assert (installation_path / 'Scripts' / 'pip.exe').exists()
    where_pip = subprocess.check_output(['where', 'pip'], env=env, universal_newlines=True).splitlines()[0].strip()
    if where_pip.strip() != str(installation_path / 'Scripts' / 'pip.exe'):
        print("cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.", file=sys.stderr)
        exit(1)

    # prepare the Python environment
    shell(['python', '-m', 'pip', 'install', '--upgrade', 'pip'] + dependency_constraint_flags, env=env)
    shell(['pip', '--version'], env=env)
    shell(['pip', 'install', '--upgrade', 'setuptools', 'wheel'] + dependency_constraint_flags, env=env)

    return env


def build(options: BuildOptions) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix='cibuildwheel'))
    built_wheel_dir = temp_dir / 'built_wheel'
    repaired_wheel_dir = temp_dir / 'repaired_wheel'

    # install nuget as best way to provide python
    nuget = Path('C:\\cibw\\nuget.exe')
    download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)

    if options.before_all:
        before_all_prepared = prepare_command(options.before_all, project='.', package=options.package_dir)
        shell([before_all_prepared])

    python_configurations = get_python_configurations(options.build_selector)
    for config in python_configurations:
        dependency_constraint_flags = []
        if options.dependency_constraints:
            dependency_constraint_flags = [
                '-c', str(options.dependency_constraints.get_for_python_version(config.version))
            ]

        # install Python
        env = setup_python(config, dependency_constraint_flags, options.environment)

        # run the before_build command
        if options.before_build:
            before_build_prepared = prepare_command(options.before_build, project='.', package=options.package_dir)
            shell([before_build_prepared], env=env)

        # build the wheel
        if built_wheel_dir.exists():
            shutil.rmtree(built_wheel_dir)
        built_wheel_dir.mkdir(parents=True)
        # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
        # see https://github.com/joerick/cibuildwheel/pull/369
        shell(['pip', 'wheel', str(options.package_dir.resolve()), '-w', str(built_wheel_dir), '--no-deps'] + get_build_verbosity_extra_flags(options.build_verbosity), env=env)
        built_wheel = next(built_wheel_dir.glob('*.whl'))

        # repair the wheel
        if repaired_wheel_dir.exists():
            shutil.rmtree(repaired_wheel_dir)
        repaired_wheel_dir.mkdir(parents=True)
        if built_wheel.name.endswith('none-any.whl') or not options.repair_command:
            # pure Python wheel or empty repair command
            built_wheel.rename(repaired_wheel_dir / built_wheel.name)
        else:
            repair_command_prepared = prepare_command(options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir)
            shell([repair_command_prepared], env=env)
        repaired_wheel = next(repaired_wheel_dir.glob('*.whl'))

        if options.test_command:
            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            shell(['pip', 'install', 'virtualenv'] + dependency_constraint_flags, env=env)
            venv_dir = Path(tempfile.mkdtemp())

            # Use --no-download to ensure determinism by using seed libraries
            # built into virtualenv
            shell(['python', '-m', 'virtualenv', '--no-download', str(venv_dir)], env=env)

            virtualenv_env = env.copy()
            virtualenv_env['PATH'] = os.pathsep.join([
                str(venv_dir / 'Scripts'),
                virtualenv_env['PATH'],
            ])

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
            shell(['pip', 'install', str(repaired_wheel) + options.test_extras], env=virtualenv_env)

            # test the wheel
            if options.test_requires:
                shell(['pip', 'install'] + options.test_requires, env=virtualenv_env)

            # run the tests from c:\, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(
                options.test_command,
                project=Path('.').resolve(),
                package=options.package_dir.resolve()
            )
            shell([test_command_prepared], cwd='c:\\', env=virtualenv_env)

            # clean up
            shutil.rmtree(venv_dir)

        # we're all done here; move it to output (remove if already exists)
        repaired_wheel.replace(options.output_dir / repaired_wheel.name)
