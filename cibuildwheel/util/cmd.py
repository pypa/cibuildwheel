import os
import shlex
import shutil
import subprocess
import sys
import typing
from collections.abc import Iterator, Mapping
from typing import Final, Literal

from ..errors import FatalError
from ..typing import PathOrStr

_IS_WIN: Final[bool] = sys.platform.startswith("win")


@typing.overload
def call(
    *args: PathOrStr,
    env: Mapping[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: Literal[False] = ...,
) -> None: ...


@typing.overload
def call(
    *args: PathOrStr,
    env: Mapping[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: Literal[True],
) -> str: ...


def call(
    *args: PathOrStr,
    env: Mapping[str, str] | None = None,
    cwd: PathOrStr | None = None,
    capture_stdout: bool = False,
) -> str | None:
    """
    Run subprocess.run, but print the commands first. Takes the commands as
    *args. Uses shell=True on Windows due to a bug. Also converts to
    Paths to strings, due to Windows behavior at least on older Pythons.
    https://bugs.python.org/issue8557
    """
    args_ = [str(arg) for arg in args]
    # print the command executing for the logs
    print("+ " + " ".join(shlex.quote(a) for a in args_))
    # workaround platform behaviour differences outlined
    # in https://github.com/python/cpython/issues/52803
    path_env = env if env is not None else os.environ
    path = path_env.get("PATH", None)
    executable = shutil.which(args_[0], path=path)
    if executable is None:
        msg = f"Couldn't find {args_[0]!r} in PATH {path!r}"
        raise FatalError(msg)
    args_[0] = executable
    try:
        result = subprocess.run(
            args_,
            check=True,
            shell=_IS_WIN,
            env=env,
            cwd=cwd,
            capture_output=capture_stdout,
            text=capture_stdout,
        )
    except subprocess.CalledProcessError as e:
        if capture_stdout:
            sys.stderr.write(e.stderr)
        raise
    if not capture_stdout:
        return None
    sys.stderr.write(result.stderr)
    return typing.cast(str, result.stdout)


def shell(
    *commands: str, env: Mapping[str, str] | None = None, cwd: PathOrStr | None = None
) -> None:
    command = " ".join(commands)
    print(f"+ {command}")
    subprocess.run(command, env=env, cwd=cwd, shell=True, check=True)


def split_command(lst: list[str]) -> Iterator[list[str]]:
    """
    Split a shell-style command, as returned by shlex.split, into a sequence
    of commands, separated by '&&'.
    """
    items = list[str]()
    for item in lst:
        if item == "&&":
            yield items
            items = []
        else:
            items.append(item)
    yield items
