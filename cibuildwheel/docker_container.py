import io
import json
import shlex
import subprocess
import sys
import uuid
from os import PathLike
from pathlib import Path, PurePath
from typing import IO, Dict, List, Optional, Sequence, Union


class DockerContainer:
    '''
    An object that represents a running Docker container.

    Intended for use as a context manager e.g.
    `with DockerContainer('ubuntu') as docker:`

    A bash shell is running in the remote container. When `call()` is invoked,
    the command is relayed to the remote shell, and the results are streamed
    back to cibuildwheel.
    '''
    UTILITY_PYTHON = '/opt/python/cp38-cp38/bin/python'

    process: subprocess.Popen
    bash_stdin: IO[bytes]
    bash_stdout: IO[bytes]

    def __init__(self, docker_image: str, simulate_32_bit=False):
        self.docker_image = docker_image
        self.simulate_32_bit = simulate_32_bit

    def __enter__(self) -> 'DockerContainer':
        self.name = f'cibuildwheel-{uuid.uuid4()}'
        shell_args = ['linux32', '/bin/bash'] if self.simulate_32_bit else ['/bin/bash']
        subprocess.run(
            [
                'docker', 'create',
                '--env', 'CIBUILDWHEEL',
                '--name', self.name,
                '-i',
                '-v', '/:/host',  # ignored on CircleCI
                self.docker_image,
                *shell_args
            ],
            check=True,
        )
        self.process = subprocess.Popen(
            [
                'docker', 'start',
                '--attach', '--interactive',
                self.name,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        assert self.process.stdin and self.process.stdout
        self.bash_stdin = self.process.stdin
        self.bash_stdout = self.process.stdout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.bash_stdin.close()
        self.process.terminate()
        self.process.wait()

        subprocess.run(['docker', 'rm', '--force', '-v', self.name])
        self.name = None

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        # `docker cp` causes 'no space left on device' error when
        # a container is running and the host filesystem is
        # mounted. https://github.com/moby/moby/issues/38995
        # Use `docker exec` instead.
        if from_path.is_dir():
            self.call(['mkdir', '-p', to_path])
            subprocess.run(
                f'tar cf - . | docker exec -i {self.name} tar -xC {to_path} -f -',
                shell=True,
                check=True,
                cwd=from_path)
        else:
            subprocess.run(
                f'cat {from_path} | docker exec -i {self.name} sh -c "cat > {to_path}"',
                shell=True,
                check=True)

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        # note: we assume from_path is a dir
        to_path.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            f'docker exec -i {self.name} tar -cC {from_path} -f - . | tar -xf -',
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
        chdir = f'cd {cwd}' if cwd else ''
        env_assignments = ' '.join(f'{shlex.quote(k)}={shlex.quote(v)}'
                                   for k, v in env.items())
        command = ' '.join(shlex.quote(str(a)) for a in args)
        end_of_message = str(uuid.uuid4())

        # log the command we're executing
        print(f'    + {command}')

        # Write a command to the remote shell. First we change the
        # cwd, if that's required. Then, we use the `env` utility to run
        # `command` inside the specified environment. We use `env` because it
        # can cope with spaces and strange characters in the name or value.
        # Finally, the remote shell is told to write a footer - this will show
        # up in the output so we know when to stop reading, and will include
        # the returncode of `command`.
        self.bash_stdin.write(bytes(f'''(
            {chdir}
            env {env_assignments} {command}
            printf "%04d%s\n" $? {end_of_message}
        )
        ''', encoding='utf8', errors='surrogateescape'))
        self.bash_stdin.flush()

        if capture_output:
            output_io: IO[bytes] = io.BytesIO()
        else:
            output_io = sys.stdout.buffer

        while True:
            line = self.bash_stdout.readline()

            if line.endswith(b'%s\n' % (bytes(end_of_message, encoding='utf8'))):
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

        if isinstance(output_io, io.BytesIO):
            output = str(output_io.getvalue(), encoding='utf8', errors='surrogateescape')
        else:
            output = ''

        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, args, output)

        return output

    def get_environment(self) -> Dict[str, str]:
        return json.loads(self.call([
            self.UTILITY_PYTHON,
            '-c',
            'import sys, json, os; json.dump(os.environ.copy(), sys.stdout)'
        ], capture_output=True))

    def environment_executor(self, command: str, environment: Dict[str, str]) -> str:
        # used as an EnvironmentExecutor to evaluate commands and capture output
        return self.call(shlex.split(command), env=environment)
