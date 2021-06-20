import os
import re
import subprocess
import sys
import textwrap

import mkdocs

EXECUTE_AND_REPLACE_TAG_REGEX = re.compile(
    r"""
        ^ # start of a line
        (?P<leading_whitespace>\s*) # leading whitespace
        ``` # opening code block tag
        python[ ]execute-and-replace\n # the instruction
        (?P<code>[\s\S]*?) # match anything non-greedily, until
        ^ # a new line
        (?P=leading_whitespace) # the same leading whitespace as we had at the start
        ``` # closing tag
    """,
    flags=re.VERBOSE | re.MULTILINE,
)


class ExecutePythonPlugin(mkdocs.plugins.BasePlugin):
    def on_page_markdown(self, markdown, page, **kwargs):
        page_src_path = page.file.abs_src_path

        def found_execute_and_replace_tag(match):
            leading_whitespace = match.group("leading_whitespace")
            code = match.group("code")

            code = textwrap.dedent(code)

            env = os.environ.copy()
            env["PAGE_SRC_PATH"] = page_src_path
            env["PYTHONUNBUFFERED"] = "1"

            result = subprocess.run(
                [sys.executable, "-c", code],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
                env=env,
            )

            output_lines = []

            for line in result.stdout.splitlines(keepends=True):
                output_lines.append(leading_whitespace + line)

            return result.stdout

        markdown = re.sub(EXECUTE_AND_REPLACE_TAG_REGEX, found_execute_and_replace_tag, markdown)
        return markdown
