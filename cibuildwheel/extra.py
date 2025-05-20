"""
These are utilities for the `/bin` scripts, not for the `cibuildwheel` program.
"""

import json
import time
import typing
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any, NotRequired, Protocol

from cibuildwheel import __version__ as cibw_version

__all__ = ("Printable", "dump_python_configurations")


class Printable(Protocol):
    def __str__(self) -> str: ...


def dump_python_configurations(
    inp: Mapping[str, Mapping[str, Sequence[Mapping[str, Printable]]]],
) -> str:
    output = StringIO()
    for header, values in inp.items():
        output.write(f"[{header}]\n")
        for inner_header, listing in values.items():
            output.write(f"{inner_header} = [\n")
            for item in listing:
                output.write("  { ")
                dict_contents = (f'{key} = "{value}"' for key, value in item.items())
                output.write(", ".join(dict_contents))
                output.write(" },\n")
            output.write("]\n")
        output.write("\n")
    # Strip the final newline, to avoid two blank lines at the end.
    return output.getvalue()[:-1]


def _json_request(request: urllib.request.Request, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return typing.cast(dict[str, Any], json.load(response))


def github_api_request(path: str, *, max_retries: int = 3) -> dict[str, Any]:
    """
    Makes a GitHub API request to the given path and returns the JSON response.
    """
    api_url = f"https://api.github.com/{path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"cibuildwheel/{cibw_version}",
    }
    request = urllib.request.Request(api_url, headers=headers)

    for retry_count in range(max_retries):
        try:
            return _json_request(request)
        except (urllib.error.URLError, TimeoutError) as e:
            # pylint: disable=E1101
            if (
                isinstance(e, urllib.error.HTTPError)
                and (e.code == 403 or e.code == 429)
                and e.headers.get("x-ratelimit-remaining") == "0"
            ):
                reset_time = int(e.headers.get("x-ratelimit-reset", 0))
                wait_time = max(0, reset_time - int(e.headers.get("date", 0)))
                print(f"Github rate limit exceeded. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)
            else:
                print(f"Retrying GitHub API request due to error: {e}")

            if retry_count == max_retries - 1:
                print(f"GitHub API request failed (Network error: {e}). Check network connection.")
                raise e

    # Should never be reached but to keep the type checker happy
    msg = "Unexpected execution path in github_api_request"
    raise RuntimeError(msg)


class PyodideXBuildEnvRelease(typing.TypedDict):
    version: str
    python_version: str
    emscripten_version: str
    min_pyodide_build_version: NotRequired[str]
    max_pyodide_build_version: NotRequired[str]


class PyodideXBuildEnvInfo(typing.TypedDict):
    releases: dict[str, PyodideXBuildEnvRelease]


def get_pyodide_xbuildenv_info() -> PyodideXBuildEnvInfo:
    xbuildenv_info_url = (
        "https://pyodide.github.io/pyodide/api/pyodide-cross-build-environments.json"
    )
    with urllib.request.urlopen(xbuildenv_info_url) as response:
        return typing.cast(PyodideXBuildEnvInfo, json.loads(response.read().decode("utf-8")))
