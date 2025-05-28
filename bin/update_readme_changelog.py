#!/usr/bin/env python3

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent / ".."
CHANGELOG_FILE = PROJECT_ROOT / "docs" / "changelog.md"

# https://regexr.com/622ds
FIRST_5_CHANGELOG_ENTRIES_REGEX = re.compile(r"""(^###.*?(?=###)){5}""", re.DOTALL | re.MULTILINE)


def mini_changelog() -> str:
    changelog_text = CHANGELOG_FILE.read_text()

    mini_changelog_match = FIRST_5_CHANGELOG_ENTRIES_REGEX.search(changelog_text)
    assert mini_changelog_match, "Failed to find the first few changelog entries"

    return f"\n{mini_changelog_match.group(0).strip()}\n"


if __name__ == "__main__":
    print(mini_changelog())
