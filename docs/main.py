import subprocess
from typing import Any

# Requires Python 3.7+


def define_env(env: Any) -> None:
    "Hook function for mkdocs-macros"

    @env.macro
    def subprocess_run(*args: str) -> str:
        "Run a subprocess and return the stdout"
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout
