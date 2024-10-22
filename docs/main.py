from __future__ import annotations

import os
import subprocess
import sysconfig
from typing import Any


def define_env(env: Any) -> None:
    "Hook function for mkdocs-macros"

    @env.macro  # type: ignore[misc]
    def subprocess_run(*args: str) -> str:
        "Run a subprocess and return the stdout"
        env = os.environ.copy()
        scripts = sysconfig.get_path("scripts")
        env["PATH"] = f"{scripts}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(args, check=True, capture_output=True, text=True, env=env).stdout
