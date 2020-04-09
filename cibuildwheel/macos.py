import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from glob import glob

from .util import (
    download,
    get_build_verbosity_extra_flags,
    prepare_command,
    get_pip_script,
    BuildOptions
)


def call(args, env=None, cwd=None, shell=False):
    # print the command executing for the logs
    if shell:
        print('+ %s' % args)
    else:
        print('+ ' + ' '.join(shlex.quote(a) for a in args))

    return subprocess.check_call(args, env=env, cwd=cwd, shell=shell)


def get_python_configurations(build_selector):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'identifier', 'url'])
    python_configurations = [
        # CPython
        PythonConfiguration(version='2.7', identifier='cp27-macosx_x86_64', url='https://www.python.org/ftp/python/2.7.17/python-2.7.17-macosx10.9.pkg'),
        PythonConfiguration(version='3.5', identifier='cp35-macosx_x86_64', url='https://www.python.org/ftp/python/3.5.4/python-3.5.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', identifier='cp36-macosx_x86_64', url='https://www.python.org/ftp/python/3.6.8/python-3.6.8-macosx10.9.pkg'),
        PythonConfiguration(version='3.7', identifier='cp37-macosx_x86_64', url='https://www.python.org/ftp/python/3.7.6/python-3.7.6-macosx10.9.pkg'),
        PythonConfiguration(version='3.8', identifier='cp38-macosx_x86_64', url='https://www.python.org/ftp/python/3.8.2/python-3.8.2-macosx10.9.pkg'),
        # PyPy
        PythonConfiguration(version='2.7', identifier='pp27-macosx_x86_64', url='https://bitbucket.org/pypy/pypy/downloads/pypy2.7-v7.3.0-osx64.tar.bz2'),
        PythonConfiguration(version='3.6', identifier='pp36-macosx_x86_64', url='https://bitbucket.org/pypy/pypy/downloads/pypy3.6-v7.3.0-osx64.tar.bz2'),
    ]

    # skip builds as required
    return [c for c in python_configurations if build_selector(c.identifier)]


SYMLINKS_DIR = '/tmp/cibw_bin'


def make_symlinks(installation_bin_path, python_executable, pip_executable):
    assert os.path.exists(os.path.join(installation_bin_path, python_executable))

    # Python bin folders on Mac don't symlink `python3` to `python`, and neither
    # does PyPy for `pypy` or `pypy3`, so we do that so `python` and `pip` always
    # point to the active configuration.
    if os.path.exists(SYMLINKS_DIR):
        shutil.rmtree(SYMLINKS_DIR)
    os.makedirs(SYMLINKS_DIR)

    os.symlink(os.path.join(installation_bin_path, python_executable), os.path.join(SYMLINKS_DIR, 'python'))
    os.symlink(os.path.join(installation_bin_path, python_executable + '-config'), os.path.join(SYMLINKS_DIR, 'python-config'))
    os.symlink(os.path.join(installation_bin_path, pip_executable), os.path.join(SYMLINKS_DIR, 'pip'))


def install_cpython(version, url):
    installed_system_packages = subprocess.check_output(['pkgutil', '--pkgs'], universal_newlines=True).splitlines()

    # if this version of python isn't installed, get it from python.org and install
    python_package_identifier = 'org.python.Python.PythonFramework-{}'.format(version)
    if python_package_identifier not in installed_system_packages:
        # download the pkg
        download(url, '/tmp/Python.pkg')
        # install
        call(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])
        # patch open ssl
        if version == '3.5':
            open_ssl_patch_url = 'https://github.com/mayeut/patch-macos-python-openssl/releases/download/v1.0.2t/patch-macos-python-%s-openssl-v1.0.2t.tar.gz' % version
            download(open_ssl_patch_url, '/tmp/python-patch.tar.gz')
            call(['sudo', 'tar', '-C', '/Library/Frameworks/Python.framework/Versions/{}/'.format(version), '-xmf', '/tmp/python-patch.tar.gz'])

    installation_bin_path = '/Library/Frameworks/Python.framework/Versions/{}/bin'.format(version)
    python_executable = 'python3' if version[0] == '3' else 'python'
    pip_executable = 'pip3' if version[0] == '3' else 'pip'
    make_symlinks(installation_bin_path, python_executable, pip_executable)

    return installation_bin_path


def install_pypy(version, url):
    pypy_tar_bz2 = url.rsplit('/', 1)[-1]
    assert pypy_tar_bz2.endswith(".tar.bz2")
    pypy_base_filename = os.path.splitext(os.path.splitext(pypy_tar_bz2)[0])[0]
    installation_path = os.path.join('/tmp', pypy_base_filename)
    if not os.path.exists(installation_path):
        download(url, os.path.join("/tmp", pypy_tar_bz2))
        call(['tar', '-C', '/tmp', '-xf', os.path.join("/tmp", pypy_tar_bz2)])

        # fix PyPy 7.3.0 bug resulting in wrong macOS platform tag
        if "-v7.3.0-" in url and version[0] == '3':
            patch_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources', 'pypy3.6.patch'))
            sysconfigdata_file = os.path.join(installation_path, 'lib_pypy', '_sysconfigdata.py')
            call(['patch', sysconfigdata_file, patch_file, '-N'])  # Always has nonzero return code

    installation_bin_path = os.path.join(installation_path, 'bin')
    python_executable = 'pypy3' if version[0] == '3' else 'pypy'
    pip_executable = 'pip3' if version[0] == '3' else 'pip'
    make_symlinks(installation_bin_path, python_executable, pip_executable)

    return installation_bin_path


def setup_python(python_configuration, dependency_constraint_flags, environment):
    if python_configuration.identifier.startswith('cp'):
        installation_bin_path = install_cpython(python_configuration.version, python_configuration.url)
    elif python_configuration.identifier.startswith('pp'):
        installation_bin_path = install_pypy(python_configuration.version, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")

    env = os.environ.copy()
    env['PATH'] = os.pathsep.join([
        SYMLINKS_DIR,
        installation_bin_path,
        env['PATH'],
    ])

    # Fix issue with site.py setting the wrong `sys.prefix`, `sys.exec_prefix`,
    # `sys.path`, ... for PyPy: https://foss.heptapod.net/pypy/pypy/issues/3175
    # Also fix an issue with the shebang of installed scripts inside the
    # testing virtualenv- see https://github.com/theacodes/nox/issues/44 and
    # https://github.com/pypa/virtualenv/issues/620
    # Also see https://github.com/python/cpython/pull/9516
    env.pop('__PYVENV_LAUNCHER__', None)
    env = environment.as_dictionary(prev_environment=env)

    # check what version we're on
    call(['which', 'python'], env=env)
    call(['python', '--version'], env=env)
    which_python = subprocess.check_output(['which', 'python'], env=env, universal_newlines=True).strip()
    if which_python != '/tmp/cibw_bin/python':
        print("cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.", file=sys.stderr)
        exit(1)

    # install pip & wheel
    call(['python', get_pip_script] + dependency_constraint_flags, env=env, cwd="/tmp")
    assert os.path.exists(os.path.join(installation_bin_path, 'pip'))
    call(['which', 'pip'], env=env)
    call(['pip', '--version'], env=env)
    which_pip = subprocess.check_output(['which', 'pip'], env=env, universal_newlines=True).strip()
    if which_pip != '/tmp/cibw_bin/pip':
        print("cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.", file=sys.stderr)
        exit(1)
    call(['pip', 'install', '--upgrade', 'setuptools', 'wheel', 'delocate'] + dependency_constraint_flags, env=env)

    # Set MACOSX_DEPLOYMENT_TARGET to 10.9, if the user didn't set it.
    # CPython 3.5 defaults to 10.6, and pypy defaults to 10.7, causing
    # inconsistencies if it's left unset.
    env.setdefault('MACOSX_DEPLOYMENT_TARGET', '10.9')

    if python_configuration.version == '3.5':
        # Cross-compilation platform override - CPython 3.5 has an
        # i386/x86_64 version of Python, but we only want a x64_64 build
        env.setdefault('_PYTHON_HOST_PLATFORM', 'macosx-10.9-x86_64')
        # https://github.com/python/cpython/blob/a5ed2fe0eedefa1649aa93ee74a0bafc8e628a10/Lib/_osx_support.py#L260
        env.setdefault('ARCHFLAGS', '-arch x86_64')

    return env


def build(options: BuildOptions):
    abs_project_dir = os.path.abspath(options.project_dir)
    temp_dir = tempfile.mkdtemp(prefix='cibuildwheel')
    built_wheel_dir = os.path.join(temp_dir, 'built_wheel')
    repaired_wheel_dir = os.path.join(temp_dir, 'repaired_wheel')

    python_configurations = get_python_configurations(options.build_selector)

    for config in python_configurations:
        dependency_constraint_flags = []
        if options.dependency_constraints:
            dependency_constraint_flags = [
                '-c', options.dependency_constraints.get_for_python_version(config.version)
            ]

        env = setup_python(config, dependency_constraint_flags, options.environment)

        # run the before_build command
        if options.before_build:
            before_build_prepared = prepare_command(options.before_build, project=abs_project_dir)
            call(before_build_prepared, env=env, shell=True)

        # build the wheel
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)
        call(['pip', 'wheel', abs_project_dir, '-w', built_wheel_dir, '--no-deps'] + get_build_verbosity_extra_flags(options.build_verbosity), env=env)
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
            call(repair_command_prepared, env=env, shell=True)
        repaired_wheel = glob(os.path.join(repaired_wheel_dir, '*.whl'))[0]

        if options.test_command:
            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            call(['pip', 'install', 'virtualenv'] + dependency_constraint_flags, env=env)
            venv_dir = tempfile.mkdtemp()

            # Use --no-download to ensure determinism by using seed libraries
            # built into virtualenv
            call(['python', '-m', 'virtualenv', '--no-download', venv_dir], env=env)

            virtualenv_env = env.copy()
            virtualenv_env['PATH'] = os.pathsep.join([
                os.path.join(venv_dir, 'bin'),
                virtualenv_env['PATH'],
            ])
            virtualenv_env["__CIBW_VIRTUALENV_PATH__"] = venv_dir

            # check that we are using the Python from the virtual environment
            call(['which', 'python'], env=virtualenv_env)

            if options.before_test:
                before_test_prepared = prepare_command(options.before_test, project=abs_project_dir)
                call(before_test_prepared, env=virtualenv_env, shell=True)

            # install the wheel
            call(['pip', 'install', repaired_wheel + options.test_extras], env=virtualenv_env)

            # test the wheel
            if options.test_requires:
                call(['pip', 'install'] + options.test_requires, env=virtualenv_env)

            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(options.test_command, project=abs_project_dir)
            call(test_command_prepared, cwd=os.environ['HOME'], env=virtualenv_env, shell=True)

            # clean up
            shutil.rmtree(venv_dir)

        # we're all done here; move it to output (overwrite existing)
        dst = os.path.join(options.output_dir, os.path.basename(repaired_wheel))
        shutil.move(repaired_wheel, dst)
