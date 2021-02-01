#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

import click
import yaml
from ghapi.core import GhApi, HTTP404NotFoundError  # type: ignore
from rich import print

from cibuildwheel.projectfiles import Analyzer

DIR = Path(__file__).parent.resolve()


def parse(contents: str) -> str | None:
    try:
        tree = ast.parse(contents)
        analyzer = Analyzer()
        analyzer.visit(tree)
        return analyzer.requires_python or ""
    except Exception:
        return None


def check_repo(name: str, contents: str) -> str:
    s = f"  {name}: "
    if name == "setup.py":
        if "python_requires" not in contents:
            s += "❌"
        res = parse(contents)
        if res is None:
            s += "⚠️ "
        elif res:
            s += "✅ " + res
        elif "python_requires" in contents:
            s += "☑️"

    elif name == "setup.cfg":
        s += "✅" if "python_requires" in contents else "❌"
    else:
        s += "✅" if "requires-python" in contents else "❌"

    return s


class MaybeRemote:
    def __init__(self, cached_file: Path | str, *, online: bool) -> None:
        self.online = online
        if self.online:
            self.contents: dict[str, dict[str, str | None]] = {
                "setup.py": {},
                "setup.cfg": {},
                "pyproject.toml": {},
            }
        else:
            with open(cached_file) as f:
                self.contents = yaml.safe_load(f)

    def get(self, repo: str, filename: str) -> str | None:
        if self.online:
            try:
                self.contents[filename][repo] = (
                    GhApi(*repo.split("/")).get_content(filename).decode()
                )
            except HTTP404NotFoundError:
                self.contents[filename][repo] = None
            return self.contents[filename][repo]
        elif repo in self.contents[filename]:
            return self.contents[filename][repo]
        else:
            raise RuntimeError(
                f"Trying to access {repo}:{filename} and not in cache, rebuild cache"
            )

    def save(self, filename: Path | str) -> None:
        with open(filename, "w") as f:
            yaml.safe_dump(self.contents, f, default_flow_style=False)

    def on_each(self, repos: list[str]) -> Iterator[tuple[str, str, str | None]]:
        for repo in repos:
            print(f"[bold]{repo}:")
            for filename in sorted(self.contents, reverse=True):
                yield repo, filename, self.get(repo, filename)


@click.command()
@click.option("--online", is_flag=True, help="Remember to set GITHUB_TOKEN")
def main(online: bool) -> None:
    with open(DIR / "../docs/data/projects.yml") as f:
        known = yaml.safe_load(f)

    repos = [x["gh"] for x in known]

    ghinfo = MaybeRemote("all_known_setup.yaml", online=online)

    for _, filename, contents in ghinfo.on_each(repos):
        if contents is None:
            print(f"[red]  {filename}: Not found")
        else:
            print(check_repo(filename, contents))

    if online:
        ghinfo.save("all_known_setup.yaml")


if __name__ == "__main__":
    main()
