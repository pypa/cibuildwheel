from __future__ import print_function
import os, subprocess, sys, uuid
from collections import namedtuple
from .util import prepare_command, get_build_verbosity_extra_flags

try:
    from shlex import quote as shlex_quote
except ImportError:
    from pipes import quote as shlex_quote


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
    ]

    # skip builds as required
    return [c for c in python_configurations if build_selector(c.identifier)]


def build(project_dir, output_dir, test_command, test_requires, test_extras, before_build, build_verbosity, build_selector, repair_command, environment, environment_test, manylinux_images):
    try:
        subprocess.check_call(['docker', '--version'])
    except:
        print('cibuildwheel: Docker not found. Docker is required to run Linux builds. '
              'If you\'re building on Travis CI, add `services: [docker]` to your .travis.yml.'
              'If you\'re building on Circle CI in Linux, add a `setup_remote_docker` step to your .circleci/config.yml',
              file=sys.stderr)
        exit(2)

    python_configurations = get_python_configurations(build_selector)
    platforms = [
        ('manylinux_x86_64', manylinux_images['x86_64']),
        ('manylinux_i686', manylinux_images['i686']),
    ]

    for platform_tag, docker_image in platforms:
        platform_configs = [c for c in python_configurations if c.identifier.endswith(platform_tag)]
        if not platform_configs:
            continue

        bash_script = '''
            set -o errexit
            set -o xtrace
            mkdir /output
            cd /project

            {environment_exports}

            for PYBIN in {pybin_paths}; do
                if [ ! -z {before_build} ]; then
                    PATH="$PYBIN:$PATH" sh -c {before_build}
                fi

                # Build the wheel
                rm -rf /tmp/built_wheel
                mkdir /tmp/built_wheel
                PATH="$PYBIN:$PATH" "$PYBIN/pip" wheel . -w /tmp/built_wheel --no-deps {build_verbosity_flag}
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
                    "$PYBIN/pip" install virtualenv
                    venv_dir=`mktemp -d`/venv
                    "$PYBIN/python" -m virtualenv "$venv_dir"

                    # run the tests in a subshell to keep that `activate`
                    # script from polluting the env
                    (
                        source "$venv_dir/bin/activate"

                        echo "Running tests using `which python`"

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
            done
        '''.format(
            pybin_paths=' '.join(c.path+'/bin' for c in platform_configs),
            test_requires=' '.join(test_requires),
            test_extras=test_extras,
            test_command=shlex_quote(
                prepare_command(test_command, project='/project') if test_command else ''
            ),
            before_build=shlex_quote(
                prepare_command(before_build, project='/project') if before_build else ''
            ),
            build_verbosity_flag=' '.join(get_build_verbosity_extra_flags(build_verbosity)),
            repair_command=shlex_quote(
                prepare_command(repair_command, wheel='"$1"', dest_dir='/tmp/repaired_wheels') if repair_command else ''
            ),
            environment_exports='\n'.join(environment.as_shell_commands()),
            uid=os.getuid(),
            gid=os.getgid(),
        )

        def run_docker(command, stdin_str=None):
            print('docker command: docker {}'.format(' '.join(map(shlex_quote, command))))
            if stdin_str is None:
                subprocess.check_call(['docker'] + command)
            else:
                args = ['docker'] + command
                process = subprocess.Popen(args, stdin=subprocess.PIPE, universal_newlines=True)
                try:
                    process.communicate(stdin_str)
                except KeyboardInterrupt:
                    process.kill()
                    process.wait()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, args)

        container_name = 'cibuildwheel-{}'.format(uuid.uuid4())
        try:
            run_docker(['create',
                        '--env', 'CIBUILDWHEEL',
                        '--name', container_name,
                        '-i',
                        '-v', '/:/host', # ignored on Circle
                        docker_image, '/bin/bash'])
            run_docker(['cp', os.path.abspath(project_dir) + '/.', container_name + ':/project'])
            run_docker(['start', '-i', '-a', container_name], stdin_str=bash_script)
            run_docker(['cp', container_name + ':/output/.', os.path.abspath(output_dir)])
        except subprocess.CalledProcessError:
            exit(1)
        finally:
            # Still gets executed, even when 'exit(1)' gets called
            run_docker(['rm', '--force', '-v', container_name])
