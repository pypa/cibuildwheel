from __future__ import print_function
import os, subprocess, shlex, sys
from collections import namedtuple
from glob import glob
try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote

from .util import prepare_command


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, skip):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'identifier', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-macosx_10_6_intel', url='https://www.python.org/ftp/python/2.7.13/python-2.7.13-macosx10.6.pkg'),
        PythonConfiguration(version='3.4', identifier='cp34-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.4.4/python-3.4.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.5', identifier='cp35-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.5.3/python-3.5.3-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', identifier='cp36-macosx_10_6_intel', url='https://www.python.org/ftp/python/3.6.0/python-3.6.0-macosx10.6.pkg'),
    ]

    def shell(args, env=None, cwd=None):
        # print the command executing for the logs
        print('+ ' + ' '.join(shlex_quote(a) for a in args))
        return subprocess.check_call(args, env=env, cwd=cwd)

    for config in python_configurations:
        if skip(config.identifier):
            print('cibuildwheel: Skipping build %s' % config.identifier, file=sys.stderr)
            continue

        # download the pkg
        shell(['curl', '-L', '-o', '/tmp/Python.pkg', config.url])
        # install
        shell(['sudo', 'installer', '-pkg', '/tmp/Python.pkg', '-target', '/'])

        env = os.environ.copy()
        env['PATH'] = os.pathsep.join([
            '/Library/Frameworks/Python.framework/Versions/%s/bin' % config.version,
            env['PATH'],
        ])

        python = 'python3' if config.version[0] == '3' else 'python2'
        pip = 'pip3' if config.version[0] == '3' else 'pip2'

        # check what version we're on
        shell(['which', python], env=env)
        shell([python, '--version'], env=env)

        # install pip & wheel
        shell([python, '-m', 'ensurepip', '--upgrade'], env=env)
        shell([pip, '--version'], env=env)
        shell([pip, 'install', 'wheel'], env=env)
        shell([pip, 'install', 'delocate'], env=env)

        # run the before_build command
        if before_build:
            before_build_prepared = prepare_command(before_build, python=python, pip=pip)
            shell(shlex.split(before_build_prepared), env=env)

        # install the package first to take care of dependencies
        shell([pip, 'install', project_dir], env=env)

        # build the wheel to temp dir
        temp_wheel_dir = '/tmp/tmpwheel%s' % config.version
        shell([pip, 'wheel', project_dir, '-w', temp_wheel_dir, '--no-deps'], env=env)
        temp_wheel = glob(temp_wheel_dir+'/*.whl')[0]

        if temp_wheel.endswith('none-any.whl'):
            # pure python wheel - just copy to output_dir
            shell(['cp', temp_wheel, output_dir], env=env)
        else:
            # list the dependencies
            shell(['delocate-listdeps', temp_wheel], env=env)
            # rebuild the wheel with shared libraries included and place in output dir
            shell(['delocate-wheel', '-w', output_dir, temp_wheel], env=env)

        # now install the package from the generated wheel
        shell([pip, 'install', package_name, '--upgrade', '--force-reinstall',
               '--no-deps', '--no-index', '--find-links', output_dir], env=env)

        # test the wheel
        if test_requires:
            shell([pip, 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            abs_project_dir = os.path.abspath(project_dir)
            test_command_absolute = test_command.format(project=abs_project_dir)
            shell(shlex.split(test_command_absolute), cwd=os.environ['HOME'], env=env)
