#!/usr/bin/env python3

"""
Convert a yaml project list into a nice table.

Suggested usage:

    ./bin/projects.py docs/data/projects.yml --online --auth $GITHUB_API_TOKEN --readme README.md
    git diff
"""

from __future__ import annotations

import builtins
import functools
import textwrap
import urllib.request
import xml.dom.minidom
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, TextIO

import click
import yaml
from github import Github, GithubException

ICONS = (
    "appveyor",
    "github",
    "azurepipelines",
    "circleci",
    "gitlab",
    "travisci",
    "windows",
    "apple",
    "linux",
)


class Project:
    NAME: int = 0

    def __init__(self, config: dict[str, Any], github: Github | None = None):
        try:
            self.name: str = config["name"]
            self.gh: str = config["gh"]
        except KeyError:
            print("Invalid config, needs at least gh and name!", config)
            raise

        self.stars_repo: str = config.get("stars", self.gh)
        self.notes: str = config.get("notes", "")
        self.ci: list[str] = config.get("ci", [])
        self.os: list[str] = config.get("os", [])

        self.online = github is not None
        if github is not None:
            try:
                repo = github.get_repo(self.stars_repo)
            except GithubException:
                print(f"Broken: {self.stars_repo}")
                raise

            self.num_stars: int = repo.stargazers_count
            self.pushed_at = repo.pushed_at
            if not self.notes:
                notes = repo.description
                if repo.description:
                    self.notes = notes
        else:
            self.num_stars = 0
            self.pushed_at = datetime.utcnow()

        name_len = len(self.name) + 4
        self.__class__.NAME = max(self.__class__.NAME, name_len)

    def __lt__(self, other: Project) -> bool:
        if self.online:
            return self.num_stars < other.num_stars
        else:
            return self.name < other.name

    @classmethod
    def header(cls) -> str:
        return textwrap.dedent(
            f"""\
                | {'Name':{cls.NAME}} | CI | OS | Notes |
                |{'':-^{cls.NAME+2  }}|----|----|:------|"""
        )

    @property
    def namelink(self) -> str:
        return f"[{self.name}][]"

    @property
    def starslink(self) -> str:
        return f"![{self.name} stars][]"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.gh}"

    @property
    def ci_icons(self) -> str:
        return " ".join(f"![{icon} icon][]" for icon in self.ci)

    @property
    def os_icons(self) -> str:
        return " ".join(f"![{icon} icon][]" for icon in self.os)

    def table_row(self) -> str:
        notes = self.notes.replace("\n", " ")
        return f"| {self.namelink: <{self.NAME}} | {self.ci_icons} | {self.os_icons} | {notes} |"

    def links(self) -> str:
        return f"[{self.name}]: {self.url}"

    def info(self) -> str:
        days = (datetime.utcnow() - self.pushed_at).days
        return f"<!-- {self.name}: {self.num_stars}, last pushed {days} days ago -->"


def fetch_icon(icon_name: str) -> None:
    url = f"https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/{icon_name}.svg"
    with urllib.request.urlopen(url) as f:
        original_svg_data = f.read()

    document = xml.dom.minidom.parseString(original_svg_data)
    svgElement = document.documentElement
    assert svgElement.nodeName == "svg"
    svgElement.setAttribute("width", "16px")
    svgElement.setAttribute("fill", "#606060")

    icon_path = path_for_icon(icon_name)
    icon_path.parent.mkdir(parents=True, exist_ok=True)

    with open(path_for_icon(icon_name), "w") as f:
        f.write(svgElement.toxml())


def path_for_icon(icon_name: str) -> Path:
    return Path(".") / "docs" / "data" / "readme_icons" / f"{icon_name}.svg"


def str_projects(
    config: list[dict[str, Any]],
    *,
    online: bool = True,
    auth: str | None = None,
) -> str:
    io = StringIO()
    print = functools.partial(builtins.print, file=io)

    if online:
        for icon in ICONS:
            fetch_icon(icon)

    github = Github(auth) if online else None

    projects = sorted((Project(item, github) for item in config), reverse=online)

    print(Project.header())
    for project in projects:
        print(project.table_row())

    print()
    for project in projects:
        print(project.links())

    print()
    for icon in ICONS:
        print(f"[{icon} icon]: {path_for_icon(icon).as_posix()}")

    print()
    for project in projects:
        print(project.info())

    return io.getvalue()


@click.command(help="Try ./bin/projects.py docs/data/projects.yml --readme README.md")
@click.argument("input", type=click.File("r"))
@click.option("--online/--no-online", default=True, help="Get info from GitHub")
@click.option("--auth", help="GitHub authentication token")
@click.option("--readme", type=click.File("r+"), help="Modify a readme file if given")
def projects(
    input: TextIO,
    online: bool,
    auth: str | None,
    readme: TextIO | None,
) -> None:
    config = yaml.safe_load(input)
    output = str_projects(config, online=online, auth=auth)

    if readme is None:
        print(output)
    else:
        text = readme.read()
        start_str = "<!-- START bin/projects.py -->\n"
        start = text.find(start_str)
        end = text.find("<!-- END bin/projects.py -->\n")
        generated_note = f"<!-- this section is generated by bin/projects.py. Don't edit it directly, instead, edit {input.name} -->"
        new_text = f"{text[:start + len(start_str)]}\n{generated_note}\n\n{output}\n{text[end:]}"

        readme.seek(0)
        readme.write(new_text)
        readme.truncate()


if __name__ == "__main__":
    projects()
