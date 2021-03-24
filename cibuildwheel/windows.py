import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Set
from zipfile import ZipFile

import toml

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .typing import PathOrStr
from .util import (
    BuildOptions,
    BuildSelector,
    NonPlatformWheelError,
    download,
    get_build_verbosity_extra_flags,
    get_pip_script,
    prepare_command,
    read_python_configs,
)

IS_RUNNING_ON_AZURE = Path('C:\\hostedtoolcache').exists()
IS_RUNNING_ON_TRAVIS = os.environ.get('TRAVIS_OS_NAME') == 'windows'


def call(args: Sequence[PathOrStr], env: Optional[Dict[str, str]] = None,
         cwd: Optional[str] = None) -> None:
    print('+ ' + ' '.join(str(a) for a in args))
    # we use shell=True here, even though we don't need a shell due to a bug
    # https://bugs.python.org/issue8557
    subprocess.run([str(a) for a in args], env=env, cwd=cwd, shell=True, check=True)


def shell(command: str, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> None:
    print(f'+ {command}')
    subprocess.run(command, env=env, cwd=cwd, shell=True, check=True)


def get_nuget_args(version: str, arch: str) -> List[str]:
    python_name = 'python' if version[0] == '3' else 'python2'
    if arch == '32':
        python_name += 'x86'
    return [python_name, '-Version', version, '-OutputDirectory', 'C:\\cibw\\python']


class PythonConfiguration(NamedTuple):
    version: str
    arch: str
    identifier: str
    url: Optional[str] = None


def get_python_configurations(
        build_selector: BuildSelector,
        architectures: Set[Architecture],
) -> List[PythonConfiguration]:

    full_python_configs = read_python_configs('windows')

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    map_arch = {
        '32': Architecture.x86,
        '64': Architecture.AMD64,
    }

    custom_compiler = os.environ.get('DISTUTILS_USE_SDK') and os.environ.get('MSSdk')
    if IS_RUNNING_ON_TRAVIS and not custom_compiler:
        # cannot install VCForPython27.msi which is needed for compiling C software
        # try with (and similar): msiexec /i VCForPython27.msi ALLUSERS=1 ACCEPT=YES /passive
        python_configurations = [c for c in python_configurations if not c.version.startswith('2.7')]

    # skip builds as required
    python_configurations = [
        c for c in python_configurations
        if build_selector(c.identifier) and map_arch[c.arch] in architectures
    ]

    return python_configurations


def extract_zip(zip_src: Path, dest: Path) -> None:
    with ZipFile(zip_src) as zip:
        zip.extractall(dest)


def install_cpython(version: str, arch: str, nuget: Path) -> Path:
    nuget_args = get_nuget_args(version, arch)
    installation_path = Path(nuget_args[-1]) / (nuget_args[0] + '.' + version) / 'tools'
    call([nuget, 'install', *nuget_args])
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


def setup_python(python_configuration: PythonConfiguration, dependency_constraint_flags: Sequence[PathOrStr], environment: ParsedEnvironment) -> Dict[str, str]:
    nuget = Path('C:\\cibw\\nuget.exe')
    if not nuget.exists():
        log.step('Downloading nuget...')
        download('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe', nuget)

    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f'Installing Python {implementation_id}...')

    if implementation_id.startswith('cp'):
        installation_path = install_cpython(python_configuration.version, python_configuration.arch, nuget)
    elif implementation_id.startswith('pp'):
        assert python_configuration.url is not None
        installation_path = install_pypy(python_configuration.version, python_configuration.arch, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")

    assert (installation_path / 'python.exe').exists()

    log.step('Setting up build environment...')

    # set up PATH and environment variables for run_with_env
    env = os.environ.copy()
    env['PYTHON_VERSION'] = python_configuration.version
    env['PYTHON_ARCH'] = python_configuration.arch
    env['PATH'] = os.pathsep.join([
        str(installation_path),
        str(installation_path / 'Scripts'),
        env['PATH']
    ])
    env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'

    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # for the logs - check we're running the right version of python
    call(['where', 'python'], env=env)
    call(['python', '--version'], env=env)
    call(['python', '-c', '"import struct; print(struct.calcsize(\'P\') * 8)"'], env=env)
    where_python = subprocess.run(['where', 'python'], env=env, universal_newlines=True, check=True, stdout=subprocess.PIPE).stdout.splitlines()[0].strip()
    if where_python != str(installation_path / 'python.exe'):
        print("cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.", file=sys.stderr)
        sys.exit(1)

    # make sure pip is installed
    if not (installation_path / 'Scripts' / 'pip.exe').exists():
        call(['python', get_pip_script, *dependency_constraint_flags], env=env, cwd="C:\\cibw")
    assert (installation_path / 'Scripts' / 'pip.exe').exists()
    where_pip = subprocess.run(['where', 'pip'], env=env, universal_newlines=True, check=True, stdout=subprocess.PIPE).stdout.splitlines()[0].strip()
    if where_pip.strip() != str(installation_path / 'Scripts' / 'pip.exe'):
        print("cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.", file=sys.stderr)
        sys.exit(1)

    log.step('Installing build tools...')

    call(['python', '-m', 'pip', 'install', '--upgrade', 'pip', *dependency_constraint_flags], env=env)
    call(['pip', '--version'], env=env)
    call(['pip', 'install', '--upgrade', 'setuptools', 'wheel', *dependency_constraint_flags], env=env)

    return env


def pep_518_cp35_workaround(package_dir: Path, env: Dict[str, str]) -> None:
    """
    Python 3.5 PEP 518 hack (see https://github.com/pypa/pip/issues/8392#issuecomment-639563494)
    Basically, nuget's Python is an embedded Python distribution, which is not supported by pip.
    Before version 3.6, there was no way to disable the "embedded" behavior, including the ignoring
    of environment variables, including the ones pip uses to setup PEP 518 builds.

    The fix here is as suggested in that issue; we manually setup the PEP 518 requirements. Since we
    are in a fresh environment (except for pinned cibuildweel dependencies), the build is already
    mostly "isolated".
    """

    pyproject_path = package_dir / 'pyproject.toml'

    if pyproject_path.exists():
        data = toml.load(pyproject_path)
        requirements = (
            data['build-system'].get('requires', [])
            if 'build-system' in data
            else []
        )

        if requirements:
            log.step('Performing PEP518 workaround...')
            with tempfile.TemporaryDirectory() as d:
                reqfile = Path(d) / "requirements.txt"
                with reqfile.open('w') as f:
                    for r in requirements:
                        print(r, file=f)
                call(['pip', 'install', '-r', reqfile], env=env)


def build(options: BuildOptions) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix='cibuildwheel'))
    built_wheel_dir = temp_dir / 'built_wheel'
    repaired_wheel_dir = temp_dir / 'repaired_wheel'

    try:
        if options.before_all:
            log.step('Running before_all...')
            env = options.environment.as_dictionary(prev_environment=os.environ)
            before_all_prepared = prepare_command(options.before_all, project='.', package=options.package_dir)
            shell(before_all_prepared, env=env)

        python_configurations = get_python_configurations(options.build_selector, options.architectures)

        for config in python_configurations:
            log.build_start(config.identifier)

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if options.dependency_constraints:
                dependency_constraint_flags = [
                    '-c', options.dependency_constraints.get_for_python_version(config.version)
                ]

            # install Python
            env = setup_python(config, dependency_constraint_flags, options.environment)

            # run the before_build command
            if options.before_build:
                log.step('Running before_build...')
                before_build_prepared = prepare_command(options.before_build, project='.', package=options.package_dir)
                shell(before_build_prepared, env=env)

            # activate the PEP 518 patch if on Windows Python 3.5
            # (will only have an effect if PEP 517 builds are used):
            if config.version.startswith('3.5'):
                pep_518_cp35_workaround(options.package_dir, env)

            log.step('Building wheel...')
            if built_wheel_dir.exists():
                shutil.rmtree(built_wheel_dir)
            built_wheel_dir.mkdir(parents=True)
            # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
            # see https://github.com/joerick/cibuildwheel/pull/369
            call([
                'pip', 'wheel',
                options.package_dir.resolve(),
                '-w', built_wheel_dir,
                '--no-deps',
                *get_build_verbosity_extra_flags(options.build_verbosity)
            ], env=env)

            built_wheel = next(built_wheel_dir.glob('*.whl'))

            # repair the wheel
            if repaired_wheel_dir.exists():
                shutil.rmtree(repaired_wheel_dir)
            repaired_wheel_dir.mkdir(parents=True)

            if built_wheel.name.endswith('none-any.whl'):
                raise NonPlatformWheelError()

            if options.repair_command:
                log.step('Repairing wheel...')
                repair_command_prepared = prepare_command(options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir)
                shell(repair_command_prepared, env=env)
            else:
                shutil.move(str(built_wheel), repaired_wheel_dir)

            repaired_wheel = next(repaired_wheel_dir.glob('*.whl'))

            if options.test_command and options.test_selector(config.identifier):
                log.step('Testing wheel...')
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.
                call(['pip', 'install', 'virtualenv', *dependency_constraint_flags], env=env)
                venv_dir = Path(tempfile.mkdtemp())

                # Use --no-download to ensure determinism by using seed libraries
                # built into virtualenv
                call(['python', '-m', 'virtualenv', '--no-download', venv_dir], env=env)

                virtualenv_env = env.copy()
                virtualenv_env['PATH'] = os.pathsep.join([
                    str(venv_dir / 'Scripts'),
                    virtualenv_env['PATH'],
                ])

                # check that we are using the Python from the virtual environment
                call(['which', 'python'], env=virtualenv_env)

                if options.before_test:
                    before_test_prepared = prepare_command(
                        options.before_test,
                        project='.',
                        package=options.package_dir
                    )
                    shell(before_test_prepared, env=virtualenv_env)

                # install the wheel
                call(['pip', 'install', str(repaired_wheel) + options.test_extras], env=virtualenv_env)

                # test the wheel
                if options.test_requires:
                    call(['pip', 'install'] + options.test_requires, env=virtualenv_env)

                # run the tests from c:\, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_command_prepared = prepare_command(
                    options.test_command,
                    project=Path('.').resolve(),
                    package=options.package_dir.resolve()
                )
                shell(test_command_prepared, cwd='c:\\', env=virtualenv_env)

                # clean up
                shutil.rmtree(venv_dir)

            # we're all done here; move it to output (remove if already exists)
            shutil.move(str(repaired_wheel), options.output_dir)
            log.build_end()
    except subprocess.CalledProcessError as error:
        log.step_end_with_error(f'Command {error.cmd} failed with code {error.returncode}. {error.stdout}')
        sys.exit(1)
