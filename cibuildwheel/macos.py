from __future__ import print_function
import os, subprocess, shlex
from collections import namedtuple
from glob import glob
try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote


def build(project_dir, package_name, output_dir, test_command, test_requires):
    PythonConfiguration = namedtuple('PythonConfiguration', ['version', 'url'])
    python_configurations = [
        PythonConfiguration(version='2.7', url='https://www.python.org/ftp/python/2.7.13/python-2.7.13-macosx10.6.pkg'),
        PythonConfiguration(version='3.4', url='https://www.python.org/ftp/python/3.4.4/python-3.4.4-macosx10.6.pkg'),
        PythonConfiguration(version='3.5', url='https://www.python.org/ftp/python/3.5.3/python-3.5.3-macosx10.6.pkg'),
        PythonConfiguration(version='3.6', url='https://www.python.org/ftp/python/3.6.0/python-3.6.0-macosx10.6.pkg'),
    ]

    def shell(args, env=None, cwd=None):
        # print the command executing for the logs
        print('+ ' + ' '.join(shlex_quote(a) for a in args))
        return subprocess.check_call(args, env=env, cwd=cwd)

    for config in python_configurations:
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
        shell(['which', pip], env=env)  # todo: remove
        shell([pip, '--version'])
        shell([pip, 'install', 'wheel'], env=env)
        shell([pip, 'install', 'delocate'], env=env)

        # build the wheel to temp dir
        temp_wheel_dir = '/tmp/tmpwheel%s' % config.version
        shell([pip, 'wheel', project_dir, '-w', temp_wheel_dir], env=env)
        temp_wheel = glob(temp_wheel_dir+'/*.whl')[0]

        # list the dependencies
        shell(['delocate-listdeps', temp_wheel], env=env)
        # rebuild the wheel with shared libraries included and place in output dir
        shell(['delocate-wheel', '-w', output_dir, temp_wheel], env=env)

        # install the wheel
        shell([pip, 'install', package_name, '--no-index', '--find-links', output_dir], env=env)

        # test the wheel
        if test_requires:
            shell([pip, '-v', 'install'] + test_requires, env=env)
        if test_command:
            # run the tests from $HOME, with an absolute path in the command
            # (this ensures that Python runs the tests against the installed wheel
            # and not the repo code)
            abs_project_dir = os.path.abspath(project_dir)
            test_command_absolute = test_command.format(project=abs_project_dir)
            shell(['which', 'nosetests'], env=env)  # todo: remove
            shell(['which', 'nosetests'], cwd=os.environ['HOME'], env=env)  # todo: remove
            shell(['nosetests', '-v'], env=env)  # todo: remove
            shell(['nosetests', '-v'], cwd=os.environ['HOME'], env=env)  # todo: remove
            shell(shlex.split(test_command_absolute), cwd=os.environ['HOME'], env=env)
