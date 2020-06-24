import io
import json
import platform
import shlex
import subprocess
import sys
import textwrap
import uuid
from os import PathLike
from pathlib import Path, PurePath
from typing import (IO, Dict, List, NamedTuple, Optional, Sequence, TextIO,
                    Union)

from .util import (BuildOptions, BuildSelector,
                   get_build_verbosity_extra_flags, prepare_command)


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
    path_str: str

    @property
    def path(self):
        return PurePath(self.path_str)


def get_python_configurations(build_selector: BuildSelector) -> List[PythonConfiguration]:
    python_configurations = [
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_x86_64', path_str='/opt/python/cp27-cp27m'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_x86_64', path_str='/opt/python/cp27-cp27mu'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_x86_64', path_str='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_x86_64', path_str='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_x86_64', path_str='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_x86_64', path_str='/opt/python/cp38-cp38'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_i686', path_str='/opt/python/cp27-cp27m'),
        PythonConfiguration(version='2.7', identifier='cp27-manylinux_i686', path_str='/opt/python/cp27-cp27mu'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_i686', path_str='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_i686', path_str='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_i686', path_str='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_i686', path_str='/opt/python/cp38-cp38'),
        PythonConfiguration(version='2.7', identifier='pp27-manylinux_x86_64', path_str='/opt/python/pp27-pypy_73'),
        PythonConfiguration(version='3.6', identifier='pp36-manylinux_x86_64', path_str='/opt/python/pp36-pypy36_pp73'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_aarch64', path_str='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_aarch64', path_str='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_aarch64', path_str='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_aarch64', path_str='/opt/python/cp38-cp38'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_ppc64le', path_str='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_ppc64le', path_str='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_ppc64le', path_str='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_ppc64le', path_str='/opt/python/cp38-cp38'),
        PythonConfiguration(version='3.5', identifier='cp35-manylinux_s390x', path_str='/opt/python/cp35-cp35m'),
        PythonConfiguration(version='3.6', identifier='cp36-manylinux_s390x', path_str='/opt/python/cp36-cp36m'),
        PythonConfiguration(version='3.7', identifier='cp37-manylinux_s390x', path_str='/opt/python/cp37-cp37m'),
        PythonConfiguration(version='3.8', identifier='cp38-manylinux_s390x', path_str='/opt/python/cp38-cp38'),
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

    cwd = Path.cwd()
    abs_package_dir = options.package_dir.resolve()
    if cwd != abs_package_dir and cwd not in abs_package_dir.parents:
        raise Exception('package_dir must be inside the working directory')

    container_package_dir = PurePath('/project') / abs_package_dir.relative_to(cwd)
    container_output_dir = PurePath('/output')

    for implementation, platform_tag, docker_image in platforms:
        platform_configs = [c for c in python_configurations if c.identifier.startswith(implementation) and c.identifier.endswith(platform_tag)]
        if not platform_configs:
            continue

        try:
            with DockerContainer(docker_image, simulate_32_bit=platform_tag.endswith('i686')) as docker:
                docker.copy_into(Path.cwd(), Path('/project'))

                if options.before_all:
                    env = docker.get_environment()
                    env['PATH'] = f'/opt/python/cp38-cp38:{env["PATH"]}'
                    env = options.environment.as_dictionary(env, executor=docker.environment_executor)

                    before_all_prepared = prepare_command(options.before_all, project='/project', package=container_package_dir)
                    docker.call(['sh', '-c', before_all_prepared], env=env)

                for config in platform_configs:
                    dependency_constraint_flags: List[Union[str, PathLike]] = []

                    if options.dependency_constraints:
                        constraints_file = options.dependency_constraints.get_for_python_version(config.version)
                        container_constraints_file = PurePath('/constraints.txt')

                        docker.copy_into(constraints_file, container_constraints_file)
                        dependency_constraint_flags = ['-c', container_constraints_file]

                    env = docker.get_environment()

                    # put this config's python top of the list
                    python_bin = config.path / 'bin'
                    env['PATH'] = f'{str(python_bin)}:{env["PATH"]}'

                    env = options.environment.as_dictionary(env, executor=docker.environment_executor)

                    # check config python and pip are still on PATH
                    which_python = docker.call(['which', 'python'], env=env, capture_output=True).strip()
                    if PurePath(which_python) != python_bin / 'python':
                        print("cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.", file=sys.stderr)
                        exit(1)

                    which_pip = docker.call(['which', 'pip'], env=env, capture_output=True).strip()
                    if PurePath(which_pip) != python_bin / 'pip':
                        print("cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.", file=sys.stderr)
                        exit(1)

                    if options.before_build:
                        before_build_prepared = prepare_command(options.before_build, project='/project', package=container_package_dir)
                        docker.call(['sh', '-c', before_build_prepared], env=env)

                    temp_dir = PurePath('/tmp/cibuildwheel')
                    built_wheel_dir = temp_dir / 'built_wheel'
                    docker.call(['rm', '-rf', built_wheel_dir])
                    docker.call(['mkdir', '-p', built_wheel_dir])

                    docker.call(
                        [
                            'pip', 'wheel',
                            container_package_dir,
                            '-w', built_wheel_dir,
                            '--no-deps',
                            *get_build_verbosity_extra_flags(options.build_verbosity)
                        ],
                        env=env,
                    )

                    built_wheel = docker.glob(built_wheel_dir / '*.whl')[0]

                    repaired_wheel_dir = temp_dir / 'repaired_wheel'
                    docker.call(['rm', '-rf', repaired_wheel_dir])
                    docker.call(['mkdir', '-p', repaired_wheel_dir])

                    if built_wheel.name.endswith('none-any.whl') or not options.repair_command:
                        docker.call(['mv', built_wheel, repaired_wheel_dir])
                    else:
                        repair_command_prepared = prepare_command(options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir)
                        docker.call(['sh', '-c', repair_command_prepared], env=env)

                    repaired_wheels = docker.glob(repaired_wheel_dir / '*.whl')

                    if options.test_command:
                        # set up a virtual environment to install and test from, to make sure
                        # there are no dependencies that were pulled in at build time.
                        docker.call(['pip', 'install', 'virtualenv', *dependency_constraint_flags], env=env)
                        venv_dir = PurePath(docker.call(['mktemp', '-d'], capture_output=True).strip()) / 'venv'

                        docker.call(['python', '-m', 'virtualenv', '--no-download', venv_dir], env=env)

                        virtualenv_env = env.copy()
                        virtualenv_env['PATH'] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"

                        if options.before_test:
                            before_test_prepared = prepare_command(options.before_test, project='/project', package=container_package_dir)
                            docker.call(['sh', '-c', before_test_prepared], env=virtualenv_env)

                        # Install the wheel we just built
                        # Note: If auditwheel produced two wheels, it's because the earlier produced wheel
                        # conforms to multiple manylinux standards. These multiple versions of the wheel are
                        # functionally the same, differing only in name, wheel metadata, and possibly include
                        # different external shared libraries. so it doesn't matter which one we run the tests on.
                        # Let's just pick the first one.
                        wheel_to_test = repaired_wheels[0]
                        docker.call(['pip', 'install', str(wheel_to_test) + options.test_extras], env=virtualenv_env)

                        # Install any requirements to run the tests
                        if options.test_requires:
                            docker.call(['pip', 'install', *options.test_requires], env=virtualenv_env)

                        # Run the tests from a different directory
                        test_command_prepared = prepare_command(options.test_command, project='/project', package=container_package_dir)
                        docker.call(['sh', '-c', test_command_prepared], cwd='/root', env=virtualenv_env)

                        # clean up test environment
                        docker.call(['rm', '-rf', venv_dir])

                    # move repaired wheels to output
                    docker.call(['mkdir', '-p', container_output_dir])
                    docker.call(['mv', *repaired_wheels, container_output_dir])

                # copy the output back into the host
                docker.copy_out(container_output_dir, options.output_dir)
        except subprocess.CalledProcessError as error:
            print(f'Command {error.cmd} failed with code {error.returncode}. {error.stdout}')
            troubleshoot(options.package_dir, error)
            exit(1)


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
            print('\n'.join([f'    {f}' for f in so_files]))
            print('')


class DockerContainer:
    UTILITY_PYTHON = '/opt/python/cp38-cp38/bin/python'

    process: subprocess.Popen
    bash_stdin: IO[str]
    bash_stdout: IO[str]

    def __init__(self, docker_image: str, simulate_32_bit=False):
        self.docker_image = docker_image
        self.simulate_32_bit = simulate_32_bit

    def __enter__(self) -> 'DockerContainer':
        self.container_name = f'cibuildwheel-{uuid.uuid4()}'
        shell_args = ['linux32', '/bin/bash'] if self.simulate_32_bit else ['/bin/bash']
        subprocess.run(
            [
                'docker', 'create',
                '--env', 'CIBUILDWHEEL',
                '--name', self.container_name,
                '-i',
                '-v', '/:/host',  # ignored on CircleCI
                self.docker_image,
                *shell_args
            ],
            check=True,
        )
        process = subprocess.Popen(
            [
                'docker', 'start',
                '--attach', '--interactive',
                self.container_name,
            ],
            encoding='utf8',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # make the input buffer large enough to carry a lot of environment
            # variables. We choose 256kB.
            bufsize=262144,
        )
        self.process = process
        assert process.stdin and process.stdout
        self.bash_stdin = process.stdin
        self.bash_stdout = process.stdout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.bash_stdin.close()
        self.process.terminate()
        self.process.wait()

        subprocess.run(['docker', 'rm', '--force', '-v', self.container_name])
        self.container_name = None

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        # `docker cp` causes 'no space left on device' error when
        # a container is running and the host filesystem is
        # mounted. https://github.com/moby/moby/issues/38995
        # Use `docker exec` instead.
        if from_path.is_dir():
            self.call(['mkdir', '-p', to_path])
            subprocess.run(
                f'tar cf - . | docker exec -i {self.container_name} tar -xC {to_path} -f -',
                shell=True,
                check=True,
                cwd=from_path)
        else:
            subprocess.run(
                f'cat {from_path} | docker exec -i {self.container_name} sh -c "cat > {to_path}"',
                shell=True,
                check=True)

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        # note: we assume from_path is a dir
        to_path.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            f'docker exec -i -w {from_path} {self.container_name} tar cf - . | tar -xf -',
            shell=True,
            check=True,
            cwd=to_path
        )

    def glob(self, pattern: PurePath) -> List[PurePath]:
        path_strs = json.loads(self.call([
            self.UTILITY_PYTHON,
            '-c',
            f'import sys, json, glob; json.dump(glob.glob({str(pattern)!r}), sys.stdout)'
        ], capture_output=True))

        return [PurePath(p) for p in path_strs]

    def call(self, args: Sequence[Union[str, PathLike]], env: Dict[str, str] = {},
             capture_output=False, cwd: Optional[Union[str, PathLike]] = None) -> str:
        env_exports = '\n'.join(f'export {k}={v}' for k, v in env.items())
        chdir = f'cd {cwd}' if cwd else ''
        command = ' '.join(shlex.quote(str(a)) for a in args)
        end_of_message = str(uuid.uuid4())

        # log the command we're executing
        print(f'    + {command}')

        # Write a command to the remote shell. First we write the
        # environment variables, exported inside the subshell. We change the
        # cwd, if that's required. Then, the command is written. Finally, the
        # remote shell is told to write a footer - this will show up in the
        # output so we know when to stop reading, and will include the
        # returncode of `command`.
        self.bash_stdin.write(f'''(
            {env_exports}
            {chdir}
            {command}
            printf "%04d%s\n" $? {end_of_message}
        )
        ''')
        self.bash_stdin.flush()

        if capture_output:
            output_io: TextIO = io.StringIO()
        else:
            output_io = sys.stdout

        while True:
            line = self.bash_stdout.readline()

            if line.endswith(end_of_message+'\n'):
                footer_offset = (
                    len(line)
                    - 1  # newline character
                    - len(end_of_message)  # delimiter
                    - 4  # 4 returncode decimals
                )
                returncode_str = line[footer_offset:footer_offset+4]
                returncode = int(returncode_str)
                # add the last line to output, without the footer
                output_io.write(line[0:footer_offset])
                break
            else:
                output_io.write(line)

        output = output_io.getvalue() if isinstance(output_io, io.StringIO) else None

        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, args, output)

        return output if output else ''

    def get_environment(self) -> Dict[str, str]:
        return json.loads(self.call([
            self.UTILITY_PYTHON,
            '-c',
            'import sys, json, os; json.dump(os.environ.copy(), sys.stdout)'
        ], capture_output=True))

    def environment_executor(self, command: str, environment: Dict[str, str]) -> str:
        # used as an EnvironmentExecutor to evaluate commands and capture output
        return self.call(shlex.split(command), env=environment)
