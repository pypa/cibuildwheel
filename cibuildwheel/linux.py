from __future__ import print_function
import os, subprocess, sys
from collections import namedtuple
from .util import prepare_command

try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote


def build(project_dir, package_name, output_dir, test_command, test_requires, before_build, skip):
    try:
        subprocess.check_call(['docker', '--version'])
    except:
        print('cibuildwheel: Docker not found. Docker is required to run Linux builds. '
              'If you\'re building on Travis CI, add `services: [docker]` to your .travis.yml.',
              file=sys.stderr)
        exit(2)

    PythonConfiguration = namedtuple('PythonConfiguration', ['identifier', 'path'])
    python_configurations = [
        PythonConfiguration(identifier='cp27-manylinux1_x86_64', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(identifier='cp27-manylinux1_x86_64', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(identifier='cp33-manylinux1_x86_64', path='/opt/python/cp33-cp33m'),
        PythonConfiguration(identifier='cp34-manylinux1_x86_64', path='/opt/python/cp34-cp34m'),
        PythonConfiguration(identifier='cp35-manylinux1_x86_64', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux1_x86_64', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp27-manylinux1_i686', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(identifier='cp27-manylinux1_i686', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(identifier='cp33-manylinux1_i686', path='/opt/python/cp33-cp33m'),
        PythonConfiguration(identifier='cp34-manylinux1_i686', path='/opt/python/cp34-cp34m'),
        PythonConfiguration(identifier='cp35-manylinux1_i686', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux1_i686', path='/opt/python/cp36-cp36m'),
    ]

    # skip builds as required
    python_configurations = [c for c in python_configurations if not skip(c.identifier)]

    platforms = [
        ('manylinux1_x86_64', 'quay.io/pypa/manylinux1_x86_64'),
        ('manylinux1_i686', 'quay.io/pypa/manylinux1_i686'),
    ]

    for platform_tag, docker_image in platforms:
        platform_configs = [c for c in python_configurations if c.identifier.endswith(platform_tag)]
        if not platform_configs:
            continue

        bash_script = '''
            set -o errexit
            set -o xtrace
            cd /project

            for PYBIN in {pybin_paths}; do
                # Setup
                rm -rf /tmp/built_wheel
                rm -rf /tmp/delocated_wheel
                mkdir /tmp/built_wheel
                mkdir /tmp/delocated_wheel

                if [ ! -z {before_build} ]; then
                    PATH=$PYBIN:$PATH sh -c {before_build}
                fi

                # Build that wheel
                "$PYBIN/pip" wheel . -w /tmp/built_wheel --no-deps
                built_wheel=(/tmp/built_wheel/*.whl)

                # Delocate the wheel
                # NOTE: 'built_wheel' here is a bash array of glob matches; "$built_wheel" returns
                # the first element
                if [[ "$built_wheel" == *none-any.whl ]]; then
                    # pure python wheel - just copy
                    mv "$built_wheel" /tmp/delocated_wheel
                else
                    auditwheel repair "$built_wheel" -w /tmp/delocated_wheel
                fi
                delocated_wheel=(/tmp/delocated_wheel/*.whl)

                # Install the wheel we just built
                "$PYBIN/pip" install "$delocated_wheel"

                # Install any requirements to run the tests
                if [ ! -z "{test_requires}" ]; then
                    "$PYBIN/pip" install {test_requires}
                fi

                # Run the tests from a different directory
                if [ ! -z {test_command} ]; then
                    pushd $HOME
                    PATH=$PYBIN:$PATH sh -c {test_command}
                    popd
                fi

                # we're all done here; move it to output
                mv "$delocated_wheel" /output
            done
        '''.format(
            package_name=package_name,
            pybin_paths=' '.join(c.path+'/bin' for c in platform_configs),
            test_requires=' '.join(test_requires),
            test_command=shlex_quote(
                test_command.format(project='/project') if test_command else ''
            ),
            before_build=shlex_quote(
                prepare_command(before_build, python='python', pip='pip') if before_build else ''
            ),
        )

        docker_process = subprocess.Popen([
                'docker',
                'run',
                '--rm',
                '-i',
                '-v', '%s:/project' % os.path.abspath(project_dir),
                '-v', '%s:/output' % os.path.abspath(output_dir),
                docker_image,
                '/bin/bash'],
            stdin=subprocess.PIPE, universal_newlines=True)

        try:
            docker_process.communicate(bash_script)
        except KeyboardInterrupt:
            docker_process.kill()
            docker_process.wait()

        if docker_process.returncode != 0:
            exit(1)
