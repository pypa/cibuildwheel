import io
import json
import os
import shlex
import subprocess
import sys
from tarfile import TarFile
import docker
from docker import DockerClient, from_env
from docker.models.containers import Container
from pathlib import Path, PurePath
from types import TracebackType
from typing import Dict, List, Optional, Sequence, Union, Type
from .typing import PathOrStr, PopenBytes

from .container import Container

class RemoteContainer(Container):
    """
    An object that represents a remote running Docker container.

    Intended for use as a context manager e.g.
    `with RemoteContainer(docker_image = 'ubuntu') as docker:`

    A bash shell is running in the remote container. When `call()` is invoked,
    the command is relayed to the remote shell, and the results are streamed
    back to cibuildwheel.
    """

    client: DockerClient
    cont: Container

    def __init__(
        self, *, docker_image: str, simulate_32_bit: bool = False, cwd: Optional[PathOrStr] = None
    ):
        super().__init__(docker_image=docker_image, simulate_32_bit=simulate_32_bit, cwd=cwd)
        self.client = from_env()

    def __enter__(self) -> "RemoteContainer":
        super().__enter__()
        cwd_arg = str(self.cwd) if isinstance(self.cwd, PurePath) else self.cwd
        shell_args = ["linux32", "/bin/bash"] if self.simulate_32_bit else ["/bin/bash"]
        image = self.client.images.pull(self.docker_image)
        self.cont = self.client.containers.create(image, name=self.name, command=shell_args, working_dir=cwd_arg, environment=['CIBUILDWHEEL=1'], network_mode="host", auto_remove=True, stdin_open=True)
        self.cont.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.cont.stop()
        super().__exit__()

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        with io.BytesIO() as mem, TarFile.open(fileobj=mem, mode='w|gz') as tar:
            tar.add(from_path, arcname=from_path.name)
            # tar.list()
            tar.close()
            mem.seek(0)
            self.cont.put_archive(to_path.parent, mem.getvalue())

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        data, stat = self.cont.get_archive(from_path, encode_stream=True)
        with io.BytesIO() as mem:
            for chk in data:
                mem.write(chk)
            mem.seek(0)
            with TarFile.open(fileobj=mem) as tar:
                members = tar.getmembers()
                root_member = members[0]
                if (root_member.isdir() and stat['isDir']):
                    members = members[1:]
                    for member in members:
                        member.name = os.path.basename(member.name)
                else:
                    root_member.name = to_path.name
                    to_path = to_path.parent

                # tar.list()
                tar.extractall(path=to_path, members=members, numeric_owner=True)

    def call(
        self,
        args: Sequence[PathOrStr],
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = False,
        binary_output: bool = False,
        cwd: Optional[PathOrStr] = None,
    ) -> Union[str, bytes]:
        env = dict() if env is None else env
        env = dict([(shlex.quote(k), shlex.quote(v)) for k, v in env.items()])
        args = shlex.join([(str(p) if isinstance(p, PurePath) else p) for p in args])
        output = self.cont.exec_run(args, workdir=cwd, environment=env, demux=False, stream=False).output
        return output if binary_output else str(output, encoding=sys.getfilesystemencoding(), errors="surrogateescape")
