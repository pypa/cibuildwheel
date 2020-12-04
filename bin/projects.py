#!/usr/bin/env python3

import json
from typing import Dict, Any, List

import click
import requests
import yaml


def get_info(gh: str) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{gh}"
    req = requests.get(url)
    return json.loads(req.content)


class Project:
    NAME: int = 0
    STARS: int = 0
    NOTES: int = 5

    def __init__(self, config: Dict[str, Any]):
        self.name: str = config["name"]
        self.gh: str = config["gh"]
        self.stars_repo: str = config.get("stars", self.gh)
        self.notes: str = config.get("notes", "")
        self.ci: List[str] = config.get("ci", [])
        self.os: List[str] = config.get("os", [])

        info = get_info(self.stars_repo)
        self.num_stars = info["stargazers_count"]

        name_len = len(self.name) + 4
        stars_len = name_len + 6

        self.__class__.NAME = max(self.__class__.NAME, name_len)
        self.__class__.STARS = max(self.__class__.STARS, stars_len)

    def __lt__(self, other: "Project") -> bool:
        return self.num_stars < other.num_stars

    @classmethod
    def header(cls):
        return (
            f"| {'Name':{cls.NAME}} | {'Stars':{cls.STARS}} | {'Notes':{cls.NOTES}} |\n"
            f"|{'':-^{cls.NAME+2}}|{'':-^{cls.STARS+2}}|:{'':-^{cls.NOTES+1}}|"
        )

    @property
    def namelink(self) -> str:
        return f"[{self.name}][]"

    @property
    def starslink(self) -> str:
        return f"[{self.name} stars][]"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.gh}"

    @property
    def starsimg(self) -> str:
        return f"https://img.shields.io/github/stars/{self.gh}label=%20&style=social"

    def table_row(self) -> str:
        return f"| {self.namelink: <{self.NAME}} | {self.starslink: <{self.STARS}} | {self.notes: <{self.NOTES}} |"

    def links(self) -> str:
        return f"[{self.name}]: {self.url}\n" f"[{self.name} stars]: {self.starsimg}"

    def info(self) -> str:
        return f"<!-- {self.name}: {self.num_stars} -->"


def print_projects(config: List[Dict[str, Any]], *, debug: bool = False) -> None:
    projects = sorted((Project(item) for item in config), reverse=True)

    print(Project.header())
    for project in projects:
        print(project.table_row())

    print()
    for project in projects:
        print(project.links())

    if debug:
        print()
        for project in projects:
            print(project.info())


@click.command()
@click.argument("input", type=click.File("r"))
@click.option("--debug/--no-debug")
def projects(input, debug):
    config = yaml.safe_load(input)
    print_projects(config, debug=debug)


if __name__ == "__main__":
    projects()
