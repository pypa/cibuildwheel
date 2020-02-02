from __future__ import print_function
import tempfile
import os, subprocess, shlex, sys, shutil
from collections import namedtuple
from glob import glob
try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

from .util import prepare_command, get_build_verbosity_extra_flags, download, get_pip_script


def get_python_configurations(build_selector):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'identifier', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-macosx_x86_64', url='https://www.python.org/ftp/python/2.7.17/python-2.7.17-macosx10.9.pkg'),
        PythonConfiguration(version='3.5', identifier='cp35-macosx_x86_64', url='https://www.python.org/ftp/python/3.5.4/python-3.5.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', identifier='cp36-macosx_x86_64', url='https://www.python.org/ftp/python/3.6.8/python-3.6.8-macosx10.9.pkg'),
        PythonConfiguration(version='3.7', identifier='cp37-macosx_x86_64', url='https://www.python.org/ftp/python/3.7.6/python-3.7.6-macosx10.9.pkg'),
        PythonConfiguration(version='3.8', identifier='cp38-macosx_x86_64', url='https://www.python.org/ftp/python/3.8.1/python-3.8.1-macosx10.9.pkg'),
    ]

    # skip builds as required
    return [c for c in python_configurations if build_selector(c.identifier)]


def build(project_dir, output_dir, test_command, test_requires, test_extras, before_build, build_verbosity, build_selector, repair_command, environment, dependency_constraints):
    abs_project_dir = os.path.abspath(project_dir)
    temp_dir = tempfile.mkdtemp(prefix='cibuildwheel')
    built_wheel_dir = os.path.join(temp_dir, 'built_wheel')
    repaired_wheel_dir = os.path.join(temp_dir, 'repaired_wheel')

    python_configurations = get_python_configurations(build_selector)

    pkgs_output = subprocess.check_output(['pkgutil',  '--pkgs'])
    if sys.version_info[0] >= 3:
        pkgs_output = pkgs_output.decode('utf8')
    installed_system_packages = pkgs_output.splitlines()

    def call(args, env=None, cwd=None, shell=False):
        # print the command executing for the logs
        if shell:
            print('+ %s' % args)
        else:
            print('+ ' + ' '.join(shlex_quote(a) for a in args))

        return subprocess.check_call(args, env=env, cwd=cwd, shell=shell)

    for config in python_configurations:
        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = 'org.python.Python.PythonFramework-%s' % config.version
        if python_package_identifier not in installed_system_packages:
            # download the pkg
            download(config.url, '/tmp/Python.pkg')
            # install
            call(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])
            # patch open ssl
            if config.version == '3.5':
                open_ssl_patch_url = 'https://github.com/mayeut/patch-macos-python-openssl/releases/download/v1.0.2t/patch-macos-python-%s-openssl-v1.0.2t.tar.gz' % config.version
                download(open_ssl_patch_url, '/tmp/python-patch.tar.gz')
                call(['sudo', 'tar', '-C', '/Library/Frameworks/Python.framework/Versions/%s/' % config.version, '-xmf', '/tmp/python-patch.tar.gz'])

        installation_bin_path = '/Library/Frameworks/Python.framework/Versions/{}/bin'.format(config.version)
        assert os.path.exists(os.path.join(installation_bin_path, 'python3' if config.version[0] == '3' else 'python'))

        # Python bin folders on Mac don't symlink python3 to python, so we do that
        # so `python` and `pip` always point to the active configuration.
        if os.path.exists('/tmp/cibw_bin'):
            shutil.rmtree('/tmp/cibw_bin')
        os.makedirs('/tmp/cibw_bin')

        if config.version[0] == '3':
            os.symlink(os.path.join(installation_bin_path, 'python3'), '/tmp/cibw_bin/python')
            os.symlink(os.path.join(installation_bin_path, 'python3-config'), '/tmp/cibw_bin/python-config')
            os.symlink(os.path.join(installation_bin_path, 'pip3'), '/tmp/cibw_bin/pip')

        env = os.environ.copy()
        env['PATH'] = os.pathsep.join([
            '/tmp/cibw_bin',
            installation_bin_path,
            env['PATH'],
        ])
        env = environment.as_dictionary(prev_environment=env)

        # check what version we're on
        call(['which', 'python'], env=env)
        call(['python', '--version'], env=env)

        dependency_constraint_flags = ['-c', dependency_constraints] if dependency_constraints else []

        # install pip & wheel
        call(['python', get_pip_script, '--no-setuptools', '--no-wheel'] + dependency_constraint_flags, env=env, cwd="/tmp")
        assert os.path.exists(os.path.join(installation_bin_path, 'pip'))
        call(['pip', '--version'], env=env)
        call(['pip', 'install', '--upgrade', 'setuptools', 'wheel', 'delocate'] + dependency_constraint_flags, env=env)

        # setup target platform, only required for python 3.5
        if config.version == '3.5':
            if '_PYTHON_HOST_PLATFORM' not in env:
                # cross-compilation platform override
                env['_PYTHON_HOST_PLATFORM'] = 'macosx-10.9-x86_64'
            if 'ARCHFLAGS' not in env:
                # https://github.com/python/cpython/blob/a5ed2fe0eedefa1649aa93ee74a0bafc8e628a10/Lib/_osx_support.py#L260
                env['ARCHFLAGS'] = '-arch x86_64'
            if 'MACOSX_DEPLOYMENT_TARGET' not in env:
                env['MACOSX_DEPLOYMENT_TARGET'] = '10.9'

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, project=abs_project_dir)
            call(before_build_prepared, env=env, shell=True)

        # build the wheel
        if os.path.exists(built_wheel_dir):
            shutil.rmtree(built_wheel_dir)
        os.makedirs(built_wheel_dir)
        call(['pip', 'wheel', abs_project_dir, '-w', built_wheel_dir, '--no-deps'] + get_build_verbosity_extra_flags(build_verbosity), env=env)
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
            call(repair_command_prepared, env=env, shell=True)
        repaired_wheel = glob(os.path.join(repaired_wheel_dir, '*.whl'))[0]

        if test_command:
            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            call(['pip', 'install', 'virtualenv'] + dependency_constraint_flags, env=env)
            venv_dir = tempfile.mkdtemp()
            call(['python', '-m', 'virtualenv', venv_dir], env=env)

            virtualenv_env = env.copy()
            virtualenv_env['PATH'] = os.pathsep.join([
                os.path.join(venv_dir, 'bin'),
                virtualenv_env['PATH'],
            ])
            # Fix some weird issue with the shebang of installed scripts
            # See https://github.com/theacodes/nox/issues/44 and https://github.com/pypa/virtualenv/issues/620
            virtualenv_env.pop('__PYVENV_LAUNCHER__', None)

            # check that we are using the Python from the virtual environment
            call(['which', 'python'], env=virtualenv_env)

            # install the wheel
            call(['pip', 'install', repaired_wheel + test_extras], env=virtualenv_env)

            # test the wheel
            if test_requires:
                call(['pip', 'install'] + test_requires, env=virtualenv_env)

            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(test_command, project=abs_project_dir)
            call(test_command_prepared, cwd=os.environ['HOME'], env=virtualenv_env, shell=True)

            # clean up
            shutil.rmtree(venv_dir)

        # we're all done here; move it to output (overwrite existing)
        dst = os.path.join(output_dir, os.path.basename(repaired_wheel))
        shutil.move(repaired_wheel, dst)
