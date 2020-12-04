#!/usr/bin/env python3

"""
Convert a yaml project list into a nice table.

Suggested usage:

    ./bin/projects.py bin/projects.yml --online --auth $GITHUB_API_TOKEN --readme README.md
    git diff
"""

import builtins
import functools
from datetime import datetime
from io import StringIO
from typing import Dict, Any, List, Optional, TextIO

import click
import yaml
from github import Github


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

    def __init__(self, config: Dict[str, Any], github: Optional[Github] = None):
        try:
            self.name: str = config["name"]
            self.gh: str = config["gh"]
        except KeyError:
            print("Invalid config, needs at least gh and name!", config)
            raise

        self.stars_repo: str = config.get("stars", self.gh)
        self.notes: str = config.get("notes", "")
        self.ci: List[str] = config.get("ci", [])
        self.os: List[str] = config.get("os", [])

        self.online = github is not None
        if github is not None:
            repo = github.get_repo(self.stars_repo)
            self.num_stars = repo.stargazers_count
            self.pushed_at = repo.pushed_at
            if not self.notes:
                notes = repo.description
                if notes:
                    self.notes = f":closed_book: {notes}"
        else:
            self.num_stars = 0
            self.pushed_at = datetime.utcnow()

        name_len = len(self.name) + 4
        self.__class__.NAME = max(self.__class__.NAME, name_len)

    def __lt__(self, other: "Project") -> bool:
        if self.online:
            return self.num_stars < other.num_stars
        else:
            return self.name < other.name

    @classmethod
    def header(cls) -> str:
        return (
            f"| {'Name':{cls.NAME}} | Stars&nbsp; | CI | OS | Notes |\n"
            f"|{'':-^{cls.NAME+2  }}|-------|----|----|:------|"
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

    @property
    def starsimg(self) -> str:
        return f"https://img.shields.io/github/stars/{self.stars_repo}?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square"

    def table_row(self) -> str:
        return f"| {self.namelink: <{self.NAME}} | {self.starslink} | {self.ci_icons} | {self.os_icons} | {self.notes} |"

    def links(self) -> str:
        return f"[{self.name}]: {self.url}\n" f"[{self.name} stars]: {self.starsimg}"

    def info(self) -> str:
        days = (datetime.utcnow() - self.pushed_at).days
        return f"<!-- {self.name}: {self.num_stars}, last pushed {days} days ago -->"


def str_projects(
    config: List[Dict[str, Any]], *, online: bool = True, auth: Optional[str] = None
) -> str:
    io = StringIO()
    print = functools.partial(builtins.print, file=io)

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
        print(
            f"[{icon} icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/{icon}.svg"
        )

    print()
    for project in projects:
        print(project.info())

    return io.getvalue()


@click.command()
@click.argument("input", type=click.File("r"))
@click.option("--online/--no-online", default=True, help="Get info from GitHub")
@click.option("--auth", help="GitHub authentication token")
@click.option("--readme", type=click.File("r+"), help="Modify a readme file if given")
def projects(
    input: TextIO, online: bool, auth: Optional[str], readme: Optional[TextIO]
) -> None:
    config = yaml.safe_load(input)
    output = str_projects(config, online=online, auth=auth)

    if readme is None:
        print(output)
    else:
        text = readme.read()
        start_str = "<!-- START bin/project.py -->\n"
        start = text.find(start_str)
        end = text.find("<!-- END bin/project.py -->\n")
        new_text = f"{text[:start + len(start_str)]}\n{output}\n{text[end:]}"

        readme.seek(0)
        readme.write(new_text)
        readme.truncate()


if __name__ == "__main__":
    projects()
