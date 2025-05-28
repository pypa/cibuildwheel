#!/usr/bin/env python3

import argparse
import dataclasses
import re
from pathlib import Path
from typing import Final

DIR: Final[Path] = Path(__file__).parent.parent.resolve()
README: Final[Path] = DIR / "README.md"
OPTIONS_MD: Final[Path] = DIR / "docs" / "options.md"

SECTION_HEADER_REGEX = re.compile(r"^## (?P<name>.*?)$", re.MULTILINE)

# https://regexr.com/8f1ff
OPTION_HEADER_REGEX = re.compile(
    r"^### (?P<name>.*?){.*#(?P<id>\S+).*}\n+> ?(?P<desc>.*)$", re.MULTILINE
)

README_OPTIONS_TABLE_SECTION = re.compile(
    r"""(?<=<!-- START bin\/update_readme_options_table.py -->\n).*(?=<!-- END bin\/update_readme_options_table.py -->)""",
    re.DOTALL,
)


@dataclasses.dataclass(kw_only=True)
class Option:
    name: str
    id: str
    desc: str
    section: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update the options table in the README from docs/options.md"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Updates the README inplace, rather than printing to stdout.",
    )
    args = parser.parse_args()

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

    table_md = "<!-- This table is auto-generated from docs/options.md by bin/update_readme_options_table.py -->\n\n"
    table_md += "|   | Option | Description |\n"
    table_md += "|---|---|---|\n"
    last_section: str | None = None

    for option in options:
        cells: list[str] = []
        cells.append(f"**{option.section}**" if option.section != last_section else "")
        last_section = option.section
        url = f"https://cibuildwheel.pypa.io/en/stable/options/#{option.id}"
        cells.append(f"[{option.name}]({url})")
        cells.append(option.desc)
        table_md += "| " + " | ".join(cells) + " |\n"
    table_md += "\n"

    if not args.force:
        print(table_md)
        return

    readme_text = README.read_text(encoding="utf-8")

    if not re.search(README_OPTIONS_TABLE_SECTION, readme_text):
        msg = "Options section not found in README"
        raise ValueError(msg)

    readme_text = re.sub(README_OPTIONS_TABLE_SECTION, table_md, readme_text)
    README.write_text(readme_text, encoding="utf-8")

    print("Updated README with options table.")


if __name__ == "__main__":
    main()
