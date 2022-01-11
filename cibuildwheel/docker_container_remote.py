import io
import os
import sys
from pathlib import Path, PurePath
from tarfile import TarFile
from types import TracebackType
from typing import Dict, Optional, Sequence, Type, Union, List, Mapping, Any, AnyStr
from contextlib import redirect_stdout
from os import fsdecode, fspath

from docker import DockerClient, from_env
from docker.models.images import Image
from docker.models.containers import Container
from docker.errors import ImageNotFound, APIError

from .container import Container
from .typing import PathOrStr
from .util import CIProvider

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
    image: Image
    cont: Container

    def __init__(
        self, *, docker_image: str, simulate_32_bit: bool = False, cwd: Optional[PathOrStr] = None
    ):
        super().__init__(docker_image=docker_image, simulate_32_bit=simulate_32_bit, cwd=cwd)
        self.client = from_env()

    def __enter__(self) -> "RemoteContainer":
        super().__enter__()
        with redirect_stdout(os.devnull):
            try:
                self.image = self.client.images.get(self.docker_image)
            except ImageNotFound:
                self.image = self.client.images.pull(self.docker_image)
            except APIError:
                pass
            finally:
                pass
        kwargs: dict[str, Any] = {}
        if self.ci_provider is None or self.ci_provider is CIProvider.travis_ci or self.ci_provider is CIProvider.other:
            kwargs["network_mode"] = "host"
        if self.cwd is not None:
            kwargs["working_dir"] = fspath(self.cwd)
        kwargs["command"] = ["linux32", "/bin/bash"] if self.simulate_32_bit else ["/bin/bash"]
        self.cont = self.client.containers.create(
            self.image,
            name=self.name,
            environment=["CIBUILDWHEEL=1"],
            auto_remove=True,
            stdin_open=True,
            **kwargs
        )
        self.cont.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.cont.stop()
        super().__exit__(exc_type, exc_val, exc_tb)

    def copy_into(self, from_path: Path, to_path: PurePath) -> None:
        with io.BytesIO() as mem, TarFile.open(fileobj=mem, mode="w|gz") as tar:
            tar.add(from_path, arcname=from_path.name)
            # tar.list()
            tar.close()
            mem.seek(0)
            self.cont.put_archive(to_path.parent, mem.getvalue())

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        # Note: assuming that `from_path` is always a directory.
        assert isinstance(from_path, PurePath)
        assert isinstance(to_path, Path)
        to_path.mkdir(parents=True, exist_ok=True)
        data, stat = self.cont.get_archive(from_path, encode_stream=True)

        with io.BytesIO() as mem:
            for chk in data:
                mem.write(chk)
            mem.seek(0)
            with TarFile.open(fileobj=mem) as tar:
                members = tar.getmembers()
                root_member = members[0]
                if root_member.isdir() and stat["isDir"]:
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
        env: Optional[Mapping[str, AnyStr]] = None,
        capture_output: bool = False,
        binary_output: bool = False,
        cwd: Optional[PathOrStr] = None,
    ) -> AnyStr:
        kwargs: dict[str, Any] = {}
        if env is not None:
            kwargs["environment"] = ['{}={}'.format(k, self.unicode_decode(v) if isinstance(v, bytes) else fspath(v)) for k, v in env.items()]
        if cwd is not None:
            kwargs["workdir"] = fspath(cwd)
        args = [(fspath(p)) for p in args]
        sys.stdout.write(f"\t + {' '.join(args)} -> ")
        try:
            code, output = self.cont.exec_run(
                args,
                demux=False,
                stream=False,
                **kwargs
            )
            sys.stdout.write(f"{code}")
        except Exception as err:
            sys.stdout.write(f"{err}")
        finally:
            sys.stdout.write("\n")
            if binary_output:
                return output
            elif capture_output:
                return fsdecode(output)
            else: return ""

    def unicode_decode(cls, b: bytes) -> str:
        return super().unicode_decode(b)
    def unicode_encode(cls, s: str) -> bytes:
        return super().unicode_encode(s)
