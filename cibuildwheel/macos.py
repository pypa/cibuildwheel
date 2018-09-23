from __future__ import print_function
import os, subprocess, shlex, sys, shutil
from collections import namedtuple
from glob import glob
try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

from .util import prepare_command, get_build_verbosity_extra_flags


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, build_verbosity, build_selector, environment):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'identifier', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-macosx_10_6_intel', url='https://www.python.org/ftp/python/2.7.15/python-2.7.15-macosx10.6.pkg'),
        PythonConfiguration(version='3.4', identifier='cp34-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.4.4/python-3.4.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.5', identifier='cp35-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.5.4/python-3.5.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', identifier='cp36-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.6.6/python-3.6.6-macosx10.6.pkg'),
        PythonConfiguration(version='3.7', identifier='cp37-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.7.0/python-3.7.0-macosx10.6.pkg'),
    ]
    get_pip_url = 'https://bootstrap.pypa.io/get-pip.py'
    get_pip_script = '/tmp/get-pip.py'

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

    abs_project_dir = os.path.abspath(project_dir)

    # get latest pip once and for all
    call(['curl', '-L', '-o', get_pip_script, get_pip_url])

    for config in python_configurations:
        if not build_selector(config.identifier):
            print('cibuildwheel: Skipping build %s' % config.identifier, file=sys.stderr)
            continue

        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = 'org.python.Python.PythonFramework-%s' % config.version
        if python_package_identifier not in installed_system_packages:
            # download the pkg
            call(['curl', '-L', '-o', '/tmp/Python.pkg', config.url])
            # install
            call(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])
            # patch open ssl
            if config.version in ('3.4', '3.5'):
                call(['curl', '-fsSLo', '/tmp/python-patch.tar.gz', 'https://github.com/mayeut/patch-macos-python-openssl/releases/download/v0.1.0/patch-macos-python-%s-openssl-v0.1.0.tar.gz' % config.version])
                call(['sudo', 'tar', '-C', '/Library/Frameworks/Python.framework/Versions/%s/' % config.version, '-xmf', '/tmp/python-patch.tar.gz'])

        installation_bin_path = '/Library/Frameworks/Python.framework/Versions/{}/bin'.format(config.version)

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

        # install pip & wheel
        call(['python', get_pip_script, '--no-setuptools', '--no-wheel'], env=env)
        call(['pip', '--version'], env=env)
        call(['pip', 'install', '--upgrade', 'setuptools'], env=env)
        call(['pip', 'install', 'wheel'], env=env)
        call(['pip', 'install', 'delocate'], env=env)

        # setup dirs
        if os.path.exists('/tmp/built_wheel'):
            shutil.rmtree('/tmp/built_wheel')
        os.makedirs('/tmp/built_wheel')
        if os.path.exists('/tmp/delocated_wheel'):
            shutil.rmtree('/tmp/delocated_wheel')
        os.makedirs('/tmp/delocated_wheel')

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, project=abs_project_dir)
            call(before_build_prepared, env=env, shell=True)

        # build the wheel
        call(['pip', 'wheel', abs_project_dir, '-w', '/tmp/built_wheel', '--no-deps'] + get_build_verbosity_extra_flags(build_verbosity), env=env)
        built_wheel = glob('/tmp/built_wheel/*.whl')[0]

        if built_wheel.endswith('none-any.whl'):
            # pure python wheel - just move
            shutil.move(built_wheel, '/tmp/delocated_wheel')
        else:
            # list the dependencies
            call(['delocate-listdeps', built_wheel], env=env)
            # rebuild the wheel with shared libraries included and place in output dir
            call(['delocate-wheel', '-w', '/tmp/delocated_wheel', built_wheel], env=env)
        delocated_wheel = glob('/tmp/delocated_wheel/*.whl')[0]

        # install the wheel
        call(['pip', 'install', delocated_wheel], env=env)

        # test the wheel
        if test_requires:
            call(['pip', 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            test_command_prepared = prepare_command(test_command, project=abs_project_dir)
            call(test_command_prepared, cwd=os.environ['HOME'], env=env, shell=True)

        # we're all done here; move it to output (overwrite existing)
        dst = os.path.join(output_dir, os.path.basename(delocated_wheel))
        shutil.move(delocated_wheel, dst)
