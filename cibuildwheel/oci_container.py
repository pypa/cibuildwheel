from __future__ import annotations

import io
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import typing
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath
from types import TracebackType
from typing import IO, Dict, Literal

from ._compat.typing import Self
from .typing import PathOrStr, PopenBytes
from .util import (
    CIProvider,
    call,
    detect_ci_provider,
    parse_key_value_string,
    strtobool,
)

ContainerEngineName = Literal["docker", "podman"]


@dataclass(frozen=True)
class OCIContainerEngineConfig:
    name: ContainerEngineName
    create_args: Sequence[str] = ()
    disable_host_mount: bool = False

    @staticmethod
    def from_config_string(config_string: str) -> OCIContainerEngineConfig:
        config_dict = parse_key_value_string(
            config_string,
            ["name"],
            ["create_args", "create-args", "disable_host_mount", "disable-host-mount"],
        )
        name = " ".join(config_dict["name"])
        if name not in {"docker", "podman"}:
            msg = f"unknown container engine {name}"
            raise ValueError(msg)

        name = typing.cast(ContainerEngineName, name)
        # some flexibility in the option names to cope with TOML conventions
        create_args = config_dict.get("create_args") or config_dict.get("create-args") or []
        disable_host_mount_options = (
            config_dict.get("disable_host_mount") or config_dict.get("disable-host-mount") or []
        )
        disable_host_mount = (
            strtobool(disable_host_mount_options[-1]) if disable_host_mount_options else False
        )

        return OCIContainerEngineConfig(
            name=name, create_args=create_args, disable_host_mount=disable_host_mount
        )

    def options_summary(self) -> str | dict[str, str]:
        if not self.create_args:
            return self.name
        else:
            return {
                "name": self.name,
                "create_args": repr(self.create_args),
                "disable_host_mount": str(self.disable_host_mount),
            }


DEFAULT_ENGINE = OCIContainerEngineConfig("docker")


class OCIContainer:
    """
    An object that represents a running OCI (e.g. Docker) container.

    Intended for use as a context manager e.g.
    `with OCIContainer(image = 'ubuntu') as docker:`

    A bash shell is running in the remote container. When `call()` is invoked,
    the command is relayed to the remote shell, and the results are streamed
    back to cibuildwheel.

    Example:
        >>> from cibuildwheel.oci_container import *  # NOQA
        >>> from cibuildwheel.options import _get_pinned_container_images
        >>> image = _get_pinned_container_images()['x86_64']['manylinux2014']
        >>> # Test the default container
        >>> with OCIContainer(image=image) as self:
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
        image: str,
        enforce_32_bit: bool = False,
        cwd: PathOrStr | None = None,
        engine: OCIContainerEngineConfig = DEFAULT_ENGINE,
    ):
        if not image:
            msg = "Must have a non-empty image to run."
            raise ValueError(msg)

        self.image = image
        self.enforce_32_bit = enforce_32_bit
        self.cwd = cwd
        self.name: str | None = None
        self.engine = engine

    def __enter__(self) -> Self:
        self.name = f"cibuildwheel-{uuid.uuid4()}"

        # work-around for Travis-CI PPC64le Docker runs since 2021:
        # this avoids network splits
        # https://github.com/pypa/cibuildwheel/issues/904
        # https://github.com/conda-forge/conda-smithy/pull/1520
        network_args = []
        if detect_ci_provider() == CIProvider.travis_ci and platform.machine() == "ppc64le":
            network_args = ["--network=host"]

        simulate_32_bit = False
        if self.enforce_32_bit:
            # If the architecture running the image is already the right one
            # or the image entrypoint takes care of enforcing this, then we don't need to
            # simulate this
            container_machine = call(
                self.engine.name, "run", "--rm", self.image, "uname", "-m", capture_stdout=True
            ).strip()
            simulate_32_bit = container_machine != "i686"

        shell_args = ["linux32", "/bin/bash"] if simulate_32_bit else ["/bin/bash"]

        subprocess.run(
            [
                self.engine.name,
                "create",
                "--env=CIBUILDWHEEL",
                "--env=SOURCE_DATE_EPOCH",
                f"--name={self.name}",
                "--interactive",
                *(["--volume=/:/host"] if not self.engine.disable_host_mount else []),
                *network_args,
                *self.engine.create_args,
                self.image,
                *shell_args,
            ],
            check=True,
        )

        self.process = subprocess.Popen(
            [
                self.engine.name,
                "start",
                "--attach",
                "--interactive",
                self.name,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        assert self.process.stdin
        assert self.process.stdout
        self.bash_stdin = self.process.stdin
        self.bash_stdout = self.process.stdout

        # run a noop command to block until the container is responding
        self.call(["/bin/true"], cwd="/")

        if self.cwd:
            # Although `docker create -w` does create the working dir if it
            # does not exist, podman does not. There does not seem to be a way
            # to setup a workdir for a container running in podman.
            self.call(["mkdir", "-p", os.fspath(self.cwd)], cwd="/")

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.bash_stdin.write(b"exit 0\n")
        self.bash_stdin.flush()
        self.process.wait(timeout=30)
        self.bash_stdin.close()
        self.bash_stdout.close()

        if self.engine.name == "podman":
            # This works around what seems to be a race condition in the podman
            # backend. The full reason is not understood. See PR #966 for a
            # discussion on possible causes and attempts to remove this line.
            # For now, this seems to work "well enough".
            self.process.wait()

        assert isinstance(self.name, str)

        keep_container = strtobool(os.environ.get("CIBW_DEBUG_KEEP_CONTAINER", ""))
        if not keep_container:
            subprocess.run(
                [self.engine.name, "rm", "--force", "-v", self.name],
                stdout=subprocess.DEVNULL,
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
                f"tar cf - . | {self.engine.name} exec -i {self.name} tar --no-same-owner -xC {shell_quote(to_path)} -f -",
                shell=True,
                check=True,
                cwd=from_path,
            )
        else:
            exec_process: subprocess.Popen[bytes]
            with subprocess.Popen(
                [
                    self.engine.name,
                    "exec",
                    "-i",
                    str(self.name),
                    "sh",
                    "-c",
                    f"cat > {shell_quote(to_path)}",
                ],
                stdin=subprocess.PIPE,
            ) as exec_process:
                assert exec_process.stdin
                with open(from_path, "rb") as from_file:
                    # Bug in mypy, https://github.com/python/mypy/issues/15031
                    shutil.copyfileobj(from_file, exec_process.stdin)  # type: ignore[misc]

                exec_process.stdin.close()
                exec_process.wait()

                if exec_process.returncode:
                    raise subprocess.CalledProcessError(
                        exec_process.returncode, exec_process.args, None, None
                    )

    def copy_out(self, from_path: PurePath, to_path: Path) -> None:
        # note: we assume from_path is a dir
        to_path.mkdir(parents=True, exist_ok=True)

        if self.engine.name == "podman":
            subprocess.run(
                [
                    self.engine.name,
                    "cp",
                    f"{self.name}:{from_path}/.",
                    str(to_path),
                ],
                check=True,
                cwd=to_path,
            )
        elif self.engine.name == "docker":
            # There is a bug in docker that prevents a simple 'cp' invocation
            # from working https://github.com/moby/moby/issues/38995
            command = f"{self.engine.name} exec -i {self.name} tar -cC {shell_quote(from_path)} -f - . | tar -xf -"
            subprocess.run(
                command,
                shell=True,
                check=True,
                cwd=to_path,
            )
        else:
            raise KeyError(self.engine.name)

    def glob(self, path: PurePosixPath, pattern: str) -> list[PurePosixPath]:
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
        env: Mapping[str, str] | None = None,
        capture_output: bool = False,
        cwd: PathOrStr | None = None,
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
                output_io.flush()
                break
            else:
                output_io.write(line)
                output_io.flush()

        if isinstance(output_io, io.BytesIO):
            output = str(output_io.getvalue(), encoding="utf8", errors="surrogateescape")
        else:
            output = ""

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, args, output)

        return output

    def get_environment(self) -> dict[str, str]:
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
        return typing.cast(Dict[str, str], env)

    def environment_executor(self, command: Sequence[str], environment: dict[str, str]) -> str:
        # used as an EnvironmentExecutor to evaluate commands and capture output
        return self.call(command, env=environment, capture_output=True)

    def debug_info(self) -> str:
        if self.engine.name == "podman":
            command = f"{self.engine.name} info --debug"
        else:
            command = f"{self.engine.name} info"
        completed = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        output = str(completed.stdout, encoding="utf8", errors="surrogateescape")
        return output


def shell_quote(path: PurePath) -> str:
    return shlex.quote(os.fspath(path))
