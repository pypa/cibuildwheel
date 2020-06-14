import os
import platform
import shlex
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path

from typing import List, NamedTuple, Optional, Union

from .util import (
    BuildOptions,
    BuildSelector,
    get_build_verbosity_extra_flags,
    prepare_command,
)


def call(args: List[str], input: Optional[Union[str, bytes]] = None, universal_newlines: bool = False) -> None:
    print('+ ' + ' '.join(shlex.quote(a) for a in args))
    subprocess.run(
        args, input=input, universal_newlines=universal_newlines, check=True
    )


def matches_platform(identifier: str) -> bool:
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


class PythonConfiguration(NamedTuple):
    version: str
    identifier: str
    path: str


def get_python_configurations(build_selector: BuildSelector) -> List[PythonConfiguration]:
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_x86_64', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_x86_64', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_x86_64', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_x86_64', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_x86_64', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_x86_64', path='/opt/python/cp38-cp38'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_i686', path='/opt/python/cp27-cp27m'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_i686', path='/opt/python/cp27-cp27mu'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_i686', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_i686', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_i686', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_i686', path='/opt/python/cp38-cp38'),
        PythonConfiguration(version='2.7', identifier='pp27-manylinux_x86_64', path='/opt/python/pp27-pypy_73'),
        PythonConfiguration(version='3.6', identifier='pp36-manylinux_x86_64', path='/opt/python/pp36-pypy36_pp73'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_aarch64', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_aarch64', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_aarch64', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_aarch64', path='/opt/python/cp38-cp38'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_ppc64le', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_ppc64le', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_ppc64le', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_ppc64le', path='/opt/python/cp38-cp38'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_s390x', path='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_s390x', path='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_s390x', path='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_s390x', path='/opt/python/cp38-cp38'),
    ]
    # skip builds as required
    return [c for c in python_configurations if matches_platform(c.identifier) and build_selector(c.identifier)]


def build(options: BuildOptions) -> None:
    try:
        subprocess.check_call(['docker', '--version'])
    except Exception:
        print('cibuildwheel: Docker not found. Docker is required to run Linux builds. '
              'If you\'re building on Travis CI, add `services: [docker]` to your .travis.yml.'
              'If you\'re building on Circle CI in Linux, add a `setup_remote_docker` step to your .circleci/config.yml',
              file=sys.stderr)
        exit(2)

    assert options.manylinux_images is not None
    python_configurations = get_python_configurations(options.build_selector)
    platforms = [
        ('cp', 'manylinux_x86_64', options.manylinux_images['x86_64']),
        ('cp', 'manylinux_i686', options.manylinux_images['i686']),
        ('cp', 'manylinux_aarch64', options.manylinux_images['aarch64']),
        ('cp', 'manylinux_ppc64le', options.manylinux_images['ppc64le']),
        ('cp', 'manylinux_s390x', options.manylinux_images['s390x']),
        ('pp', 'manylinux_x86_64', options.manylinux_images['pypy_x86_64']),
    ]

    pwd = Path().resolve()
    abs_package_dir = options.package_dir.resolve()
    if pwd != abs_package_dir and pwd not in abs_package_dir.parents:
        raise Exception('package_dir must be inside the working directory')

    container_package_dir = Path('/project') / abs_package_dir.relative_to(pwd)

    for implementation, platform_tag, docker_image in platforms:
        platform_configs = [c for c in python_configurations if c.identifier.startswith(implementation) and c.identifier.endswith(platform_tag)]
        if not platform_configs:
            continue

        shell_cmd = ['linux32', '/bin/bash'] if platform_tag.endswith("i686") else ['/bin/bash']

        container_name = f'cibuildwheel-{uuid.uuid4()}'
        call(['docker', 'create',
              '--env', 'CIBUILDWHEEL',
              '--name', container_name,
              '-i',
              '-v', '/:/host',  # ignored on CircleCI
              docker_image,
              '/bin/bash'])

        try:
            call(['docker', 'cp', '.', container_name + ':/project'])

            call(['docker', 'start', container_name])

            for config in platform_configs:
                if options.dependency_constraints:
                    constraints_file = options.dependency_constraints.get_for_python_version(config.version)

                    # `docker cp` causes 'no space left on device' error when
                    # a container is running and the host filesystem is
                    # mounted. https://github.com/moby/moby/issues/38995
                    # Use `docker exec` instead.
                    with open(constraints_file, 'rb') as f:
                        call(
                            ['docker', 'exec', '-i', container_name, 'sh', '-c', 'cat > /constraints.txt'],
                            input=f.read(),
                        )

                call(
                    ['docker', 'exec', '-i', container_name] + shell_cmd,
                    universal_newlines=True,
                    input='''
                        # give xtrace output an extra level of indent inside docker
                        PS4='    + '

                        set -o errexit
                        set -o xtrace
                        mkdir -p /output
                        cd /project

                        PYBIN="{config_python_bin}"

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
                            pip install {dependency_install_flags} virtualenv
                            venv_dir=`mktemp -d`/venv
                            python -m virtualenv --no-download "$venv_dir"

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
                        for repaired_wheel in "${{repaired_wheels[@]}}"; do
                            chown {uid}:{gid} "/output/$(basename "$repaired_wheel")"
                        done
                    '''.format(
                        config_python_bin=config.path + '/bin',
                        package_dir=container_package_dir,
                        test_requires=' '.join(options.test_requires),
                        test_extras=options.test_extras,
                        test_command=shlex.quote(
                            prepare_command(options.test_command, project='/project', package=container_package_dir) if options.test_command else ''
                        ),
                        before_build=shlex.quote(
                            prepare_command(options.before_build, project='/project', package=container_package_dir) if options.before_build else ''
                        ),
                        build_verbosity_flag=' '.join(get_build_verbosity_extra_flags(options.build_verbosity)),
                        repair_command=shlex.quote(
                            prepare_command(options.repair_command, wheel='"$1"', dest_dir='/tmp/repaired_wheels') if options.repair_command else ''
                        ),
                        environment_exports='\n'.join(options.environment.as_shell_commands()),
                        uid=os.getuid(),
                        gid=os.getgid(),
                        before_test=shlex.quote(
                            prepare_command(options.before_test, project='/project', package=container_package_dir) if options.before_test else ''
                        ),
                        dependency_install_flags='-c /constraints.txt' if options.dependency_constraints else '',
                    )
                )

            # copy the output back into the host
            call(['docker', 'cp',
                  container_name + ':/output/.',
                  str(options.output_dir.resolve())])
        except subprocess.CalledProcessError as error:
            troubleshoot(options.package_dir, error)
            exit(1)
        finally:
            # Still gets executed, even when 'exit(1)' gets called
            call(['docker', 'rm', '--force', '-v', container_name])


def troubleshoot(package_dir: Path, error: Exception) -> None:
    if (isinstance(error, subprocess.CalledProcessError) and 'exec' in error.cmd):
        # the bash script failed
        print('Checking for common errors...')
        so_files = list(package_dir.glob('**/*.so'))

        if so_files:
            print(textwrap.dedent('''
                NOTE: Shared object (.so) files found in this project.

                  These files might be built against the wrong OS, causing problems with
                  auditwheel.

                  If you're using Cython and have previously done an in-place build,
                  remove those build files (*.so and *.c) before starting cibuildwheel.
            '''))

            print('  Files detected:')
            print('\n'.join(['    ' + str(f) for f in so_files]))
            print('')
