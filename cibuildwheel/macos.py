from __future__ import print_function
import os, subprocess, shlex, sys, shutil
from collections import namedtuple
from glob import glob
try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

from .util import prepare_command


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, skip, environment):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'identifier', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-macosx_10_6_intel', url='https://www.python.org/ftp/python/2.7.13/python-2.7.13-macosx10.6.pkg'),
        PythonConfiguration(version='3.4', identifier='cp34-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.4.4/python-3.4.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.5', identifier='cp35-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.5.3/python-3.5.3-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', identifier='cp36-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.6.2/python-3.6.2-macosx10.6.pkg'),
    ]

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
        if skip(config.identifier):
            print('cibuildwheel: Skipping build %s' % config.identifier, file=sys.stderr)
            continue

        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = 'org.python.Python.PythonFramework-%s' % config.version
        if python_package_identifier not in installed_system_packages:
            # download the pkg
            call(['curl', '-L', '-o', '/tmp/Python.pkg', config.url])
            # install
            call(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])

        env = os.environ.copy()
        env['PATH'] = os.pathsep.join([
            '/Library/Frameworks/Python.framework/Versions/%s/bin' % config.version,
            env['PATH'],
        ])
        env = environment.as_dictionary(prev_environment=env)

        python = 'python3' if config.version[0] == '3' else 'python2'
        pip = 'pip3' if config.version[0] == '3' else 'pip2'

        # check what version we're on
        call(['which', python], env=env)
        call([python, '--version'], env=env)

        # install pip & wheel
        call([python, '-m', 'ensurepip', '--upgrade'], env=env)
        call([pip, '--version'], env=env)
        call([pip, 'install', 'wheel'], env=env)
        call([pip, 'install', 'delocate'], env=env)

        # setup dirs
        if os.path.exists('/tmp/built_wheel'):
            shutil.rmtree('/tmp/built_wheel')
        os.makedirs('/tmp/built_wheel')
        if os.path.exists('/tmp/delocated_wheel'):
            shutil.rmtree('/tmp/delocated_wheel')
        os.makedirs('/tmp/delocated_wheel')

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, python=python, pip=pip)
            call(before_build_prepared, env=env, shell=True)

        # build the wheel
        call([pip, 'wheel', project_dir, '-w', '/tmp/built_wheel', '--no-deps'], env=env)
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
        call([pip, 'install', delocated_wheel], env=env)

        # test the wheel
        if test_requires:
            call([pip, 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            abs_project_dir = os.path.abspath(project_dir)
            test_command_absolute = test_command.format(project=abs_project_dir)
            call(shlex.split(test_command_absolute), cwd=os.environ['HOME'], env=env)

        # we're all done here; move it to output
        shutil.move(delocated_wheel, output_dir)
