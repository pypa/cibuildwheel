#!/usr/bin/env python3

import dataclasses
import re
from pathlib import Path
from typing import Final

DIR: Final[Path] = Path(__file__).parent.parent.resolve()
OPTIONS_MD: Final[Path] = DIR / "docs" / "options.md"

SECTION_HEADER_REGEX = re.compile(r"^## (?P<name>.*?)$", re.MULTILINE)

# https://regexr.com/8f1ff
OPTION_HEADER_REGEX = re.compile(
    r"^### (?P<name>.*?){.*#(?P<id>\S+).*}\n+> ?(?P<desc>.*)$", re.MULTILINE
)


@dataclasses.dataclass(kw_only=True)
class Option:
    name: str
    id: str
    desc: str
    section: str


def get_table() -> str:
    options_md = OPTIONS_MD.read_text(encoding="utf-8")

    sections = SECTION_HEADER_REGEX.split(options_md)[1:]

    options = []

    for section_name, section_content in zip(sections[0::2], sections[1::2], strict=True):
        for match in OPTION_HEADER_REGEX.finditer(section_content):
            option = Option(
                name=match.group("name").strip(),
                id=match.group("id").strip(),
                desc=match.group("desc").strip(),
                section=section_name.strip(),
            )
            options.append(option)

    table_md = "\n<!-- This table is auto-generated from docs/options.md by bin/readme_options_table.py -->\n\n"
    table_md += "|   | Option | Description |\n"
    table_md += "|---|---|---|\n"
    last_section: str | None = None

    for option in options:
        cells: list[str] = []

        cells.append(f"**{option.section}**" if option.section != last_section else "")
        last_section = option.section

        url = f"https://cibuildwheel.pypa.io/en/stable/options/#{option.id}"
        name = option.name.replace(", ", "<br>")  # Replace commas with line breaks
        cells.append(f"[{name}]({url})")

        cells.append(option.desc)

        table_md += "| " + " | ".join(cells) + " |\n"
    table_md += "\n"

    return table_md


if __name__ == "__main__":
    print(get_table())
