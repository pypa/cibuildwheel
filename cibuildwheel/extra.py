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
from typing import Any, Protocol

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

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return typing.cast(dict[str, Any], json.load(response))

    except (urllib.error.URLError, TimeoutError) as e:
        # pylint: disable=E1101
        if max_retries > 0:
            if (
                isinstance(e, urllib.error.HTTPError)
                and (e.code == 403 or e.code == 429)
                and e.get("x-ratelimit-remaining") == "0"
            ):
                reset_time = int(e.get("x-ratelimit-reset", 0))
                wait_time = max(0, reset_time - int(e.get("date", 0)))
                print(f"Github rate limit exceeded. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)
            else:
                print(f"Retrying GitHub API request due to error: {e}")
            return github_api_request(path, max_retries=max_retries - 1)
        else:
            print(f"GitHub API request failed (Network error: {e}). Check network connection.")
            raise e
