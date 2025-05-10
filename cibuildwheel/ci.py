import os
import re
from enum import Enum

from .util.helpers import strtobool


class CIProvider(Enum):
    # official support
    travis_ci = "travis"
    circle_ci = "circle_ci"
    azure_pipelines = "azure_pipelines"
    github_actions = "github_actions"
    gitlab = "gitlab"
    cirrus_ci = "cirrus_ci"

    # unofficial support
    appveyor = "appveyor"

    other = "other"


def detect_ci_provider() -> CIProvider | None:
    if "TRAVIS" in os.environ:
        return CIProvider.travis_ci
    elif "APPVEYOR" in os.environ:
        return CIProvider.appveyor
    elif "CIRCLECI" in os.environ:
        return CIProvider.circle_ci
    elif "AZURE_HTTP_USER_AGENT" in os.environ:
        return CIProvider.azure_pipelines
    elif "GITHUB_ACTIONS" in os.environ:
        return CIProvider.github_actions
    elif "GITLAB_CI" in os.environ:
        return CIProvider.gitlab
    elif "CIRRUS_CI" in os.environ:
        return CIProvider.cirrus_ci
    elif strtobool(os.environ.get("CI", "false")):
        return CIProvider.other
    else:
        return None


def fix_ansi_codes_for_github_actions(text: str) -> str:
    """
    Github Actions forgets the current ANSI style on every new line. This
    function repeats the current ANSI style on every new line.
    """
    ansi_code_regex = re.compile(r"(\033\[[0-9;]*m)")
    ansi_codes: list[str] = []
    output = ""

    for line in text.splitlines(keepends=True):
        # add the current ANSI codes to the beginning of the line
        output += "".join(ansi_codes) + line

        # split the line at each ANSI code
        parts = ansi_code_regex.split(line)
        # if there are any ANSI codes, save them
        if len(parts) > 1:
            # iterate over the ANSI codes in this line
            for code in parts[1::2]:
                if code == "\033[0m":
                    # reset the list of ANSI codes when the clear code is found
                    ansi_codes = []
                else:
                    ansi_codes.append(code)

    return output
