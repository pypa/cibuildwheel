import os
import re
import subprocess
import sysconfig
from typing import Any

import rich.console
import rich.text


def define_env(env: Any) -> None:
    "Hook function for mkdocs-macros"

    @env.macro  # type: ignore[misc]
    def subprocess_run(*args: str) -> str:
        "Run a subprocess and return the stdout"
        env = os.environ.copy()
        scripts = sysconfig.get_path("scripts")
        env.pop("NO_COLOR", None)
        env["PATH"] = f"{scripts}{os.pathsep}{env.get('PATH', '')}"
        env["PYTHON_COLORS"] = "1"
        output = subprocess.run(args, check=True, capture_output=True, text=True, env=env).stdout
        rich_text = rich.text.Text.from_ansi(output)
        console = rich.console.Console(record=True, force_terminal=True)
        console.print(rich_text)
        page = console.export_html(inline_styles=True)
        result = re.search(r"<body.*?>(.*?)</body>", page, re.DOTALL | re.IGNORECASE)
        assert result
        txt = result.group(1).strip()
        return txt.replace("code ", 'code class="nohighlight" ')
