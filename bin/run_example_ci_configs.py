#!/usr/bin/env python3


import os
import shutil
import subprocess
import sys
import textwrap
import time
import typing
from pathlib import Path
from urllib.parse import quote

import click

DIR = Path(__file__).parent.resolve()


def shell(cmd: str, *, check: bool, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([cmd], shell=True, check=check, **kwargs)  # type: ignore[call-overload, no-any-return]


def git_repo_has_changes() -> bool:
    unstaged_changes = shell("git diff-index --quiet HEAD --", check=False).returncode != 0
    staged_changes = shell("git diff-index --quiet --cached HEAD --", check=False).returncode != 0
    return unstaged_changes or staged_changes


def generate_basic_project(path: Path) -> None:
    sys.path.insert(0, "")
    from test.test_projects.c import new_c_project

    project = new_c_project()
    project.generate(path)


class CIService(typing.NamedTuple):
    name: str
    dst_config_path: str
    badge_md: str


services = [
    CIService(
        name="azure-pipelines",
        dst_config_path="azure-pipelines.yml",
        badge_md="[![Build Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/pypa.cibuildwheel?branchName={branch})](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=2&branchName={branch})",
    ),
    CIService(
        name="circleci",
        dst_config_path=".circleci/config.yml",
        badge_md="[![CircleCI](https://circleci.com/gh/pypa/cibuildwheel/tree/{branch_escaped}.svg?style=svg)](https://circleci.com/gh/pypa/cibuildwheel/tree/{branch})",
    ),
    CIService(
        name="github",
        dst_config_path=".github/workflows/example.yml",
        badge_md="[![Build](https://github.com/pypa/cibuildwheel/workflows/Build/badge.svg?branch={branch})](https://github.com/pypa/cibuildwheel/actions)",
    ),
    CIService(
        name="travis-ci",
        dst_config_path=".travis.yml",
        badge_md="[![Build Status](https://app.travis-ci.com/pypa/cibuildwheel.svg?branch={branch})](https://app.travis-ci.com/pypa/cibuildwheel)",
    ),
    CIService(
        name="gitlab",
        dst_config_path=".gitlab-ci.yml",
        badge_md="[![Gitlab](https://gitlab.com/joerick/cibuildwheel/badges/{branch}/pipeline.svg)](https://gitlab.com/joerick/cibuildwheel/-/commits/{branch})",
    ),
    CIService(
        name="cirrus-ci",
        dst_config_path=".cirrus.yml",
        badge_md="[![Cirrus CI](https://api.cirrus-ci.com/github/pypa/cibuildwheel.svg?branch={branch})](https://cirrus-ci.com/github/pypa/cibuildwheel/{branch})",
    ),
]


def ci_service_for_config_file(config_file: Path) -> CIService:
    filename = config_file.name
    try:
        return next(s for s in services if filename.startswith(s.name))
    except StopIteration:
        msg = f"unknown ci service for config file {config_file}"
        raise ValueError(msg) from None


@click.command()
@click.argument("config_files", nargs=-1, type=click.Path())
def run_example_ci_configs(config_files=None):
    """
    Test the example configs. If no files are specified, will test
    examples/*-minimal.yml
    """

    if len(config_files) == 0:
        config_files = Path("examples").glob("*-minimal.yml")

    # check each CI service has at most 1 config file
    configs_by_service = set()
    for config_file in config_files:
        service = ci_service_for_config_file(config_file)
        if service.name in configs_by_service:
            msg = "You cannot specify more than one config per CI service"
            raise Exception(msg)
        configs_by_service.add(service.name)

    if git_repo_has_changes():
        print("Your git repo has uncommitted changes. Commit or stash before continuing.")
        sys.exit(1)

    previous_branch = shell(
        "git rev-parse --abbrev-ref HEAD", check=True, capture_output=True, encoding="utf8"
    ).stdout.strip()

    timestamp = time.strftime("%Y-%m-%dT%H-%M-%S", time.gmtime())
    branch_name = f"example-config-test---{previous_branch}-{timestamp}"

    try:
        shell(f"git checkout --orphan {branch_name}", check=True)

        example_project = Path("example_root")
        generate_basic_project(example_project)

        for config_file in config_files:
            service = ci_service_for_config_file(config_file)
            dst_config_file = example_project / service.dst_config_path

            dst_config_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(config_file, dst_config_file)

        subprocess.run(["git", "add", example_project], check=True)
        message = textwrap.dedent(
            f"""\
            Test example minimal configs

            Testing files: {[str(f) for f in config_files]}
            Generated from branch: {previous_branch}
            Time: {timestamp}
            """
        )
        subprocess.run(["git", "commit", "--no-verify", "--message", message], check=True)
        shell(f"git subtree --prefix={example_project} push origin {branch_name}", check=True)

        print("---")
        print()
        print("> **Examples test run**")
        print("> ")
        print(f"> Branch: [{branch_name}](https://github.com/pypa/cibuildwheel/tree/{branch_name})")
        print("> ")
        print("> | Service | Config | Status |")
        print("> |---|---|---|")
        for config_file in config_files:
            service = ci_service_for_config_file(config_file)
            badge = service.badge_md.format(
                branch=branch_name, branch_escaped=quote(branch_name, safe="")
            )
            print(f"> | {service.name} | `{config_file}` | {badge} |")
        print("> ")
        print("> Generated by `bin/run_example_ci_config.py`")
        print()
        print("---")
    finally:
        # remove any local changes
        shutil.rmtree(example_project, ignore_errors=True)
        shell("git checkout -- .", check=True)
        shell(f"git checkout {previous_branch}", check=True)
        shell(f"git branch -D --force {branch_name}", check=True)


if __name__ == "__main__":
    os.chdir(DIR)
    run_example_ci_configs(standalone_mode=True)
