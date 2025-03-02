#!/usr/bin/env python3

"""
Check known projects for usage of requires-python.

Usage:

    ./bin/inspect_all_known_projects.py --online=$GITHUB_TOKEN

This will cache the results to all_known_setup.yaml; you can reprint
the results without the `--online` setting.
"""

import ast
from collections.abc import Iterable, Iterator
from pathlib import Path

import click
import yaml
from github import Github, GithubException
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
    github: Github | None
    contents: dict[str, dict[str, str | None]]

    def __init__(self, cached_file: Path | str, *, online: str | None) -> None:
        if online is not None:
            self.github = Github(online)
            self.contents = {
                "setup.py": {},
                "setup.cfg": {},
                "pyproject.toml": {},
            }
        else:
            self.github = None
            with open(cached_file) as f:
                self.contents = yaml.safe_load(f)

    def get(self, repo: str, filename: str) -> str | None:
        if self.github:
            try:
                gh_file = self.github.get_repo(repo).get_contents(filename)
            except GithubException:
                self.contents[filename][repo] = None
            else:
                assert not isinstance(gh_file, list)
                self.contents[filename][repo] = gh_file.decoded_content.decode(encoding="utf-8")

            return self.contents[filename][repo]
        elif repo in self.contents[filename]:
            return self.contents[filename][repo]
        else:
            msg = f"Trying to access {repo}:{filename} and not in cache, rebuild cache"
            raise RuntimeError(msg)

    def save(self, filename: Path | str) -> None:
        with open(filename, "w") as f:
            yaml.safe_dump(self.contents, f, default_flow_style=False)

    def on_each(self, repos: Iterable[str]) -> Iterator[tuple[str, str, str | None]]:
        for repo in repos:
            print(f"[bold]{repo}:")
            for filename in sorted(self.contents, reverse=True):
                yield repo, filename, self.get(repo, filename)


@click.command()
@click.option("--online", help="Set to $GITHUB_TOKEN")
def main(online: str | None) -> None:
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
