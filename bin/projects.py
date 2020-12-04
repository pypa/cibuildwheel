#!/usr/bin/env python3

import json
from typing import Dict, Any, List
from datetime import datetime

import click
import requests
import yaml


def get_info(gh: str) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{gh}"
    req = requests.get(url)
    return json.loads(req.content)


class Project:
    NAME: int = 0
    ONLINE: bool = True

    def __init__(self, config: Dict[str, Any]):
        self.name: str = config["name"]
        self.gh: str = config["gh"]
        self.stars_repo: str = config.get("stars", self.gh)
        self.notes: str = config.get("notes", "")
        self.ci: List[str] = config.get("ci", [])
        self.os: List[str] = config.get("os", [])

        if self.ONLINE:
            info = get_info(self.stars_repo)
            self.num_stars = info["stargazers_count"]
            self.pushed_at = datetime.strptime(info["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
        else:
            self.num_stars = 0
            self.pushed_at = datetime.utcnow()

        name_len = len(self.name) + 4
        self.__class__.NAME = max(self.__class__.NAME, name_len)

    def __lt__(self, other: "Project") -> bool:
        if self.ONLINE:
            return self.num_stars < other.num_stars
        else:
            return self.name < other.name

    @classmethod
    def header(cls):
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


def print_projects(config: List[Dict[str, Any]], *, debug: bool = False, online: bool = True) -> None:
    Project.ONLINE = online
    projects = sorted((Project(item) for item in config), reverse=online)

    print(Project.header())
    for project in projects:
        print(project.table_row())

    print()
    for project in projects:
        print(project.links())

    print()
    for icon in {"appveyor", "github", "azure-pipelines", "circleci", "gitlab", "travisci", "windows", "apple", "linux"}:
        print(f"[{icon} icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/{icon}.svg")

    if debug:
        print()
        for project in projects:
            print(project.info())


@click.command()
@click.argument("input", type=click.File("r"))
@click.option("--debug/--no-debug")
@click.option("--online/--no-online", default=True)
def projects(input: click.File, debug: bool, online: bool) -> None:
    config = yaml.safe_load(input)
    print_projects(config, debug=debug, online=online)


if __name__ == "__main__":
    projects()
