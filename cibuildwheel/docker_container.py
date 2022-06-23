import io
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path, PurePath, PurePosixPath
from types import TracebackType
from typing import IO, Dict, List, Optional, Sequence, Type, cast

from cibuildwheel.util import CIProvider, detect_ci_provider

from .typing import PathOrStr, PopenBytes


class DockerContainer:
    """
    An object that represents a running Docker container.

    Intended for use as a context manager e.g.
    `with DockerContainer(docker_image = 'ubuntu') as docker:`

    A bash shell is running in the remote container. When `call()` is invoked,
    the command is relayed to the remote shell, and the results are streamed
    back to cibuildwheel.

    TODO:
        - [ ] Rename to Container as this now generalizes docker and podman?

    Example:
        >>> from cibuildwheel.docker_container import *  # NOQA
        >>> from cibuildwheel.options import _get_pinned_docker_images
        >>> docker_image = _get_pinned_docker_images()['x86_64']['manylinux2014']
        >>> # Test the default container
        >>> with DockerContainer(docker_image=docker_image) as self:
        ...     self.call(["echo", "hello world"])
        ...     self.call(["cat", "/proc/1/cgroup"])
        ...     print(self.get_environment())
        ...     print(self.debug_info())
    """

    UTILITY_PYTHON = "/opt/python/cp38-cp38/bin/python"

    process: PopenBytes
    bash_stdin: IO[bytes]
    bash_stdout: IO[bytes]

    def __init__(
        self,
        *,
        docker_image: str,
        simulate_32_bit: bool = False,
        cwd: Optional[PathOrStr] = None,
        container_engine: str = "docker",
        env: Optional[Dict[str, str]] = None,
    ):
        if not docker_image:
            raise ValueError("Must have a non-empty docker image to run.")

        self.docker_image = docker_image
        self.simulate_32_bit = simulate_32_bit
        self.cwd = cwd
        self.name: Optional[str] = None
        self.container_engine = container_engine
        self.env = env  # If specified, overwrite environment variables

    def __enter__(self) -> "DockerContainer":

        self.name = f"cibuildwheel-{uuid.uuid4()}"

        # work-around for Travis-CI PPC64le Docker runs since 2021:
        # this avoids network splits
        # https://github.com/pypa/cibuildwheel/issues/904
        # https://github.com/conda-forge/conda-smithy/pull/1520
        network_args = []
        if detect_ci_provider() == CIProvider.travis_ci and platform.machine() == "ppc64le":
            network_args = ["--network=host"]

        shell_args = ["linux32", "/bin/bash"] if self.simulate_32_bit else ["/bin/bash"]

        subprocess.run(
            [
                self.container_engine,
                "create",
                "--env=CIBUILDWHEEL",
                f"--name={self.name}",
                "--interactive",
                *network_args,
                # Z-flags is for SELinux
                "--volume=/:/host:Z",  # ignored on CircleCI
                self.docker_image,
                *shell_args,
            ],
            env=self.env,
            check=True,
        )

        self.process = subprocess.Popen(
            [
                self.container_engine,
                "start",
                "--attach",
                "--interactive",
                self.name,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=self.env,
        )

        assert self.process.stdin and self.process.stdout
        self.bash_stdin = self.process.stdin
        self.bash_stdout = self.process.stdout

        # run a noop command to block until the container is responding
        self.call(["/bin/true"], cwd="")

        if self.cwd:
            # Although `docker create -w` does create the working dir if it
            # does not exist, podman does not. There does not seem to be a way
            # to setup a workdir for a container running in podman.
            self.call(["mkdir", "-p", str(self.cwd)], cwd="")

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:

        self.bash_stdin.write(b"exit 0\n")
        self.bash_stdin.flush()
        self.process.wait(timeout=30)
        self.bash_stdin.close()
        self.bash_stdout.close()

        if self.container_engine == "podman":
            # This works around what seems to be a race condition in the podman
            # backend. The full reason is not understood. See PR #966 for a
            # discussion on possible causes and attempts to remove this line.
            # For now, this seems to work "well enough".
            self.process.wait()

        assert isinstance(self.name, str)

        subprocess.run(
            [self.container_engine, "rm", "--force", "-v", self.name],
            stdout=subprocess.DEVNULL,
            env=self.env,
            check=False,
        )
        self.name = None

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        # `docker cp` causes 'no space left on device' error when
        # a container is running and the host filesystem is
        # mounted. https://github.com/moby/moby/issues/38995
        # Use `docker exec` instead.

        if from_path.is_dir():
            self.call(["mkdir", "-p", to_path])
            subprocess.run(
                f"tar cf - . | {self.container_engine} exec -i {self.name} tar --no-same-owner -xC {shell_quote(to_path)} -f -",
                shell=True,
                check=True,
                cwd=from_path,
                env=self.env,
            )
        else:
            with subprocess.Popen(
                [
                    self.container_engine,
                    "exec",
                    "-i",
                    str(self.name),
                    "sh",
                    "-c",
                    f"cat > {shell_quote(to_path)}",
                ],
                env=self.env,
                stdin=subprocess.PIPE,
            ) as docker:
                docker.stdin = cast(IO[bytes], docker.stdin)

                with open(from_path, "rb") as from_file:
                    shutil.copyfileobj(from_file, docker.stdin)

                docker.stdin.close()
                docker.wait()

                if docker.returncode:
                    raise subprocess.CalledProcessError(docker.returncode, docker.args, None, None)

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        # note: we assume from_path is a dir
        to_path.mkdir(parents=True, exist_ok=True)

        if self.container_engine == "podman":
            # The copy out logic that works for docker does not seem to
            # translate to podman, which seems to need the steps spelled out
            # more explicitly.
            command = f"{self.container_engine} exec -i {self.name} tar -cC {shell_quote(from_path)} -f /tmp/output-{self.name}.tar ."
            subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=to_path,
                env=self.env,
            )

            command = f"{self.container_engine} cp {self.name}:/tmp/output-{self.name}.tar output-{self.name}.tar"
            subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=to_path,
                env=self.env,
            )
            command = f"tar -xvf output-{self.name}.tar"
            subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=to_path,
                env=self.env,
            )
            os.unlink(to_path / f"output-{self.name}.tar")
        elif self.container_engine == "docker":
            command = f"{self.container_engine} exec -i {self.name} tar -cC {shell_quote(from_path)} -f - . | tar -xf -"
            subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=to_path,
                env=self.env,
            )
        else:
            raise KeyError(self.container_engine)

    def glob(self, path: PurePosixPath, pattern: str) -> List[PurePosixPath]:
        glob_pattern = path.joinpath(pattern)

        path_strings = json.loads(
            self.call(
                [
                    self.UTILITY_PYTHON,
                    "-c",
                    f"import sys, json, glob; json.dump(glob.glob({str(glob_pattern)!r}), sys.stdout)",
                ],
                capture_output=True,
            )
        )

        return [PurePosixPath(p) for p in path_strings]

    def call(
        self,
        args: Sequence[PathOrStr],
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = False,
        cwd: Optional[PathOrStr] = None,
    ) -> str:

        if cwd is None:
            # Podman does not start the a container in a specific working dir
            # so we always need to specify it when making calls.
            cwd = self.cwd

        chdir = f"cd {cwd}" if cwd else ""
        env_assignments = (
            " ".join(f"{shlex.quote(k)}={shlex.quote(v)}" for k, v in env.items())
            if env is not None
            else ""
        )
        command = " ".join(shlex.quote(str(a)) for a in args)
        end_of_message = str(uuid.uuid4())

        # log the command we're executing
        print(f"    + {command}")

        # Write a command to the remote shell. First we change the
        # cwd, if that's required. Then, we use the `env` utility to run
        # `command` inside the specified environment. We use `env` because it
        # can cope with spaces and strange characters in the name or value.
        # Finally, the remote shell is told to write a footer - this will show
        # up in the output so we know when to stop reading, and will include
        # the return code of `command`.
        self.bash_stdin.write(
            bytes(
                f"""(
            {chdir}
            env {env_assignments} {command}
            printf "%04d%s\n" $? {end_of_message}
        )
        """,
                encoding="utf8",
                errors="surrogateescape",
            )
        )
        self.bash_stdin.flush()

        if capture_output:
            output_io: IO[bytes] = io.BytesIO()
        else:
            output_io = sys.stdout.buffer

        while True:
            line = self.bash_stdout.readline()

            if line.endswith(bytes(end_of_message, encoding="utf8") + b"\n"):
                # fmt: off
                footer_offset = (
                    len(line)
                    - 1  # newline character
                    - len(end_of_message)  # delimiter
                    - 4  # 4 return code decimals
                )
                # fmt: on
                return_code_str = line[footer_offset : footer_offset + 4]
                return_code = int(return_code_str)
                # add the last line to output, without the footer
                output_io.write(line[0:footer_offset])
                break
            else:
                output_io.write(line)

        if isinstance(output_io, io.BytesIO):
            output = str(output_io.getvalue(), encoding="utf8", errors="surrogateescape")
        else:
            output = ""

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, args, output)

        return output

    def get_environment(self) -> Dict[str, str]:
        env = json.loads(
            self.call(
                [
                    self.UTILITY_PYTHON,
                    "-c",
                    "import sys, json, os; json.dump(os.environ.copy(), sys.stdout)",
                ],
                capture_output=True,
            )
        )
        return cast(Dict[str, str], env)

    def environment_executor(self, command: List[str], environment: Dict[str, str]) -> str:
        # used as an EnvironmentExecutor to evaluate commands and capture output
        return self.call(command, env=environment, capture_output=True)

    def debug_info(self) -> str:
        if self.container_engine == "podman":
            command = f"{self.container_engine} info --debug"
        else:
            command = f"{self.container_engine} info"
        completed = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        output = str(completed.stdout, encoding="utf8", errors="surrogateescape")
        return output


def shell_quote(path: PurePath) -> str:
    return shlex.quote(str(path))
