import os
import platform
import shlex
import subprocess
import sys
import textwrap
import uuid
from collections import namedtuple

from .util import (
    get_build_verbosity_extra_flags,
    prepare_command,
)


def matches_platform(identifier):
    pm = platform.machine()
    if pm == "x86_64":
        # x86_64 machines can run i686 docker containers
        if identifier.endswith('x86_64') or identifier.endswith('i686'):
            return True
    elif pm == "i686":
        if identifier.endswith('i686'):
            return True
    elif pm == "aarch64":
        if identifier.endswith('aarch64'):
            return True
    elif pm == "ppc64le":
        if identifier.endswith('ppc64le'):
            return True
    elif pm == "s390x":
        if identifier.endswith('s390x'):
            return True
    return False


def get_python_configurations(build_selector):
    PythonConfiguration = namedtuple('PythonConfiguration', ['identifier', 'path'])
    python_configurations = [
        PythonConfiguration(identifier='cp27-manylinux_x86_64', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(identifier='cp27-manylinux_x86_64', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(identifier='cp35-manylinux_x86_64', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux_x86_64', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp37-manylinux_x86_64', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(identifier='cp38-manylinux_x86_64', path='/opt/python/cp38-cp38'),
        PythonConfiguration(identifier='cp27-manylinux_i686', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(identifier='cp27-manylinux_i686', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(identifier='cp35-manylinux_i686', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux_i686', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp37-manylinux_i686', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(identifier='cp38-manylinux_i686', path='/opt/python/cp38-cp38'),
        PythonConfiguration(identifier='pp27-manylinux_x86_64', path='/opt/python/pp27-pypy_73'),
        PythonConfiguration(identifier='pp36-manylinux_x86_64', path='/opt/python/pp36-pypy36_pp73'),
        PythonConfiguration(identifier='cp35-manylinux_aarch64', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux_aarch64', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp37-manylinux_aarch64', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(identifier='cp38-manylinux_aarch64', path='/opt/python/cp38-cp38'),
        PythonConfiguration(identifier='cp35-manylinux_ppc64le', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux_ppc64le', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp37-manylinux_ppc64le', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(identifier='cp38-manylinux_ppc64le', path='/opt/python/cp38-cp38'),
        PythonConfiguration(identifier='cp35-manylinux_s390x', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(identifier='cp36-manylinux_s390x', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(identifier='cp37-manylinux_s390x', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(identifier='cp38-manylinux_s390x', path='/opt/python/cp38-cp38'),
    ]
    # skip builds as required
    return [c for c in python_configurations if matches_platform(c.identifier) and build_selector(c.identifier)]


def build(project_dir, output_dir, test_command, before_test, test_requires, test_extras, before_build, build_verbosity, build_selector, repair_command, environment, manylinux_images):
    try:
        subprocess.check_call(['docker', '--version'])
    except Exception:
        print('cibuildwheel: Docker not found. Docker is required to run Linux builds. '
              'If you\'re building on Travis CI, add `services: [docker]` to your .travis.yml.'
              'If you\'re building on Circle CI in Linux, add a `setup_remote_docker` step to your .circleci/config.yml',
              file=sys.stderr)
        exit(2)

    python_configurations = get_python_configurations(build_selector)
    platforms = [
        ('cp', 'manylinux_x86_64', manylinux_images['x86_64']),
        ('cp', 'manylinux_i686', manylinux_images['i686']),
        ('cp', 'manylinux_aarch64', manylinux_images['aarch64']),
        ('cp', 'manylinux_ppc64le', manylinux_images['ppc64le']),
        ('cp', 'manylinux_s390x', manylinux_images['s390x']),
        ('pp', 'manylinux_x86_64', manylinux_images['pypy_x86_64']),
    ]

    abs_project_dir = os.path.abspath(project_dir)
    abs_package_dir = os.path.abspath(package_dir)

    container_project_dir = '/project'
    container_package_dir = os.path.join(container_project_dir, os.path.relpath(abs_package_dir, os.path.commonprefix([abs_project_dir, abs_package_dir]))),

    for implementation, platform_tag, docker_image in platforms:
        platform_configs = [c for c in python_configurations if c.identifier.startswith(implementation) and c.identifier.endswith(platform_tag)]
        if not platform_configs:
            continue

        bash_script = '''
            set -o errexit
            set -o xtrace
            mkdir /output
            cd /project

            for PYBIN in {pybin_paths}; do (
                # Temporary hack/workaround, putting loop body in subshell; fixed in PR #256

                export PATH="$PYBIN:$PATH"
                {environment_exports}

                # check the active python and pip are in PYBIN
                if [ "$(which pip)" != "$PYBIN/pip" ]; then
                    echo "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it."
                    exit 1
                fi
                if [ "$(which python)" != "$PYBIN/python" ]; then
                    echo "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it."
                    exit 1
                fi

                if [ ! -z {before_build} ]; then
                    sh -c {before_build}
                fi

                # Build the wheel
                rm -rf /tmp/built_wheel
                mkdir /tmp/built_wheel
                pip wheel {package_dir} -w /tmp/built_wheel --no-deps {build_verbosity_flag}
                built_wheel=(/tmp/built_wheel/*.whl)

                # repair the wheel
                rm -rf /tmp/repaired_wheels
                mkdir /tmp/repaired_wheels
                # NOTE: 'built_wheel' here is a bash array of glob matches; "$built_wheel" returns
                # the first element
                if [[ "$built_wheel" == *none-any.whl ]] || [ -z {repair_command} ]; then
                    # pure Python wheel or empty repair command
                    mv "$built_wheel" /tmp/repaired_wheels
                else
                    sh -c {repair_command} repair_command "$built_wheel"
                fi
                repaired_wheels=(/tmp/repaired_wheels/*.whl)

                if [ ! -z {test_command} ]; then
                    # Set up a virtual environment to install and test from, to make sure
                    # there are no dependencies that were pulled in at build time.
                    pip install virtualenv
                    venv_dir=`mktemp -d`/venv
                    python -m virtualenv "$venv_dir"

                    export __CIBW_VIRTUALENV_PATH__=$venv_dir

                    # run the tests in a subshell to keep that `activate`
                    # script from polluting the env
                    (
                        source "$venv_dir/bin/activate"

                        echo "Running tests using `which python`"

                        if [ ! -z {before_test} ]; then
                            sh -c {before_test}
                        fi

                        # Install the wheel we just built
                        # Note: If auditwheel produced two wheels, it's because the earlier produced wheel
                        # conforms to multiple manylinux standards. These multiple versions of the wheel are
                        # functionally the same, differing only in name, wheel metadata, and possibly include
                        # different external shared libraries. so it doesn't matter which one we run the tests on.
                        # Let's just pick the first one.
                        pip install "${{repaired_wheels[0]}}"{test_extras}

                        # Install any requirements to run the tests
                        if [ ! -z "{test_requires}" ]; then
                            pip install {test_requires}
                        fi

                        # Run the tests from a different directory
                        pushd $HOME
                        sh -c {test_command}
                        popd
                    )
                    # exit if tests failed (needed for older bash versions)
                    if [ $? -ne 0 ]; then
                        exit 1;
                    fi

                    # clean up
                    rm -rf "$venv_dir"
                fi

                # we're all done here; move it to output
                mv "${{repaired_wheels[@]}}" /output
                for repaired_wheel in "${{repaired_wheels[@]}}"; do chown {uid}:{gid} "/output/$(basename "$repaired_wheel")"; done
            ) done
        '''.format(
            pybin_paths=' '.join(c.path + '/bin' for c in platform_configs),
            package_dir=container_package_dir,
            test_requires=' '.join(test_requires),
            test_extras=test_extras,
            test_command=shlex.quote(
                prepare_command(test_command, project=container_project_dir, package=container_package_dir) if test_command else ''
            ),
            before_build=shlex.quote(
                prepare_command(before_build, project=container_project_dir, package=container_package_dir) if before_build else ''
            ),
            build_verbosity_flag=' '.join(get_build_verbosity_extra_flags(build_verbosity)),
            repair_command=shlex.quote(
                prepare_command(repair_command, wheel='"$1"', dest_dir='/tmp/repaired_wheels') if repair_command else ''
            ),
            environment_exports='\n'.join(environment.as_shell_commands()),
            uid=os.getuid(),
            gid=os.getgid(),
            before_test=shlex.quote(
                prepare_command(before_test, project=container_project_dir, package=container_package_dir) if before_test else ''
            ),
        )

        container_name = 'cibuildwheel-{}'.format(uuid.uuid4())
        try:
            subprocess.run(['docker', 'create',
                            '--env', 'CIBUILDWHEEL',
                            '--name', container_name,
                            '-i',
                            '-v', '/:/host',  # ignored on CircleCI
                            docker_image, '/bin/bash'], check=True)
            subprocess.run(['docker', 'cp', os.path.abspath(project_dir) + '/.', container_name + ':/project'], check=True)
            subprocess.run(['docker', 'start', '-i', '-a', container_name], input=bash_script, universal_newlines=True, check=True)
            subprocess.run(['docker', 'cp', container_name + ':/output/.', os.path.abspath(output_dir)], check=True)
        except subprocess.CalledProcessError as error:
            troubleshoot(project_dir, error)
            exit(1)
        finally:
            # Still gets executed, even when 'exit(1)' gets called
            subprocess.run(['docker', 'rm', '--force', '-v', container_name], check=True)


def troubleshoot(project_dir, error):
    if (isinstance(error, subprocess.CalledProcessError) and 'start' in error.cmd):
        # the bash script failed
        print('Checking for common errors...')
        so_files = []
        for root, dirs, files in os.walk(project_dir):
            for name in files:
                _, ext = os.path.splitext(name)
                if ext == '.so':
                    so_files.append(os.path.join(root, name))

        if so_files:
            print(textwrap.dedent('''
                NOTE: Shared object (.so) files found in this project.

                  These files might be built against the wrong OS, causing problems with
                  auditwheel.

                  If you're using Cython and have previously done an in-place build,
                  remove those build files (*.so and *.c) before starting cibuildwheel.
            '''))

            print('  Files detected:')
            print('\n'.join(['    ' + f for f in so_files]))
            print('')
