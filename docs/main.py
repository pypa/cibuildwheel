import subprocess
from typing import Any

# Requires Python 3.7+


def define_env(env: Any) -> None:
    "Hook function for mkdocs-macros"

    @env.macro
    def cibuildwheel_help_txt() -> str:
        return subprocess.run(
            ["cibuildwheel", "--help"], check=True, capture_output=True, text=True
        ).stdout
