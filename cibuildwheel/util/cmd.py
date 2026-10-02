from __future__ import annotations

__lazy_modules__ = {"cibuildwheel.errors", "shlex", "shutil", "subprocess"}

import os
import shlex
import shutil
import subprocess
import sys
import typing

from cibuildwheel.errors import FatalError

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from typing import Final, Literal

    from cibuildwheel.typing import PathOrStr

# characters that no shell treats specially, so they never need quoting
_BARE_CHARS: Final[frozenset[str]] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@%+=:,./-_"
)
# characters that a shell would still act on inside double quotes
_ACTIVE_IN_DOUBLE_QUOTES: Final[frozenset[str]] = frozenset("`$\\")


def format_command_for_display(args: Iterable[PathOrStr]) -> str:
    """
    Render a command as a string that's pleasant to read in a log.

    This is for display only. Don't build a command out of it - use
    shlex.quote for anything that will actually be run.

    shlex.quote always uses single quotes, so an argument that itself contains
    a single quote comes out as unreadable '"'"' soup. Where it's unambiguous
    we leave the argument bare, or wrap it in double quotes so its single
    quotes survive intact, and otherwise fall back to shlex.quote.
    """
    return " ".join(_quote_for_display(str(arg)) for arg in args)


def _quote_for_display(arg: str) -> str:
    if arg and _BARE_CHARS.issuperset(arg):
        return arg
    if "'" in arg and _ACTIVE_IN_DOUBLE_QUOTES.isdisjoint(arg):
        return '"' + arg.replace('"', '\\"') + '"'
    return shlex.quote(arg)


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
    *args. Resolves the executable with shutil.which so PATH/PATHEXT lookup
    matches across platforms (https://github.com/python/cpython/issues/52803).
    Path arguments are converted to strings.
    """
    args_ = [str(arg) for arg in args]
    # print the command executing for the logs
    print("+ " + format_command_for_display(args_))
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
            # Workaround for PyPy 3.9 https://github.com/pypy/pypy/issues/4958
            # shutil.which resolved to an uppercase suffix but pypy can't
            # create a venv when called like that.
            executable=(
                f"{executable[:-4]}.exe"
                if sys.platform == "win32" and executable.endswith(".EXE")
                else None
            ),
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
    return typing.cast("str", result.stdout)


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
