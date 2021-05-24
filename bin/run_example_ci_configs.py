#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import sys
import textwrap
import time
from collections import namedtuple
from glob import glob
from pathlib import Path
from subprocess import run
from urllib.parse import quote

import click


def shell(cmd, **kwargs):
    return run([cmd], shell=True, **kwargs)


def git_repo_has_changes():
    unstaged_changes = shell("git diff-index --quiet HEAD --").returncode != 0
    staged_changes = shell("git diff-index --quiet --cached HEAD --").returncode != 0
    return unstaged_changes or staged_changes


def generate_basic_project(path):
    sys.path.insert(0, "")
    from test.test_projects.c import new_c_project

    project = new_c_project()
    project.generate(path)


CIService = namedtuple("CIService", "name dst_config_path badge_md")
services = [
    CIService(
        name="appveyor",
        dst_config_path="appveyor.yml",
        badge_md="[![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/{branch}?svg=true)](https://ci.appveyor.com/project/pypa/cibuildwheel/branch/{branch})",
    ),
    CIService(
        name="azure-pipelines",
        dst_config_path="azure-pipelines.yml",
        badge_md="[![Build Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/joerick.cibuildwheel?branchName={branch})](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=2&branchName={branch})",
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
        badge_md="[![Build Status](https://travis-ci.org/pypa/cibuildwheel.svg?branch={branch})](https://travis-ci.org/pypa/cibuildwheel)",
    ),
    CIService(
        name="gitlab",
        dst_config_path=".gitlab-ci.yml",
        badge_md="[![Gitlab](https://gitlab.com/pypa/cibuildwheel/badges/{branch}/pipeline.svg)](https://gitlab.com/pypa/cibuildwheel/-/commits/{branch})",
    ),
]


def ci_service_for_config_file(config_file):
    service_name = Path(config_file).name.rsplit("-", 1)[0]

    for service in services:
        if service.name == service_name:
            return service

    raise ValueError(f"unknown ci service for config file {config_file}")


@click.command()
@click.argument("config_files", nargs=-1, type=click.Path())
def run_example_ci_configs(config_files=None):
    """
    Test the example configs. If no files are specified, will test
    examples/*-minimal.yml
    """

    if len(config_files) == 0:
        config_files = glob("examples/*-minimal.yml")

    # check each CI service has at most 1 config file
    configs_by_service = {}
    for config_file in config_files:
        service = ci_service_for_config_file(config_file)
        if service.name in configs_by_service:
            raise Exception("You cannot specify more than one config per CI service")
        configs_by_service[service.name] = config_file

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
            src_config_file = Path(config_file)
            dst_config_file = example_project / service.dst_config_path

            dst_config_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_config_file, dst_config_file)

        run(["git", "add", example_project], check=True)
        message = textwrap.dedent(
            f"""\
            Test example minimal configs

            Testing files: {config_files}
            Generated from branch: {previous_branch}
            Time: {timestamp}
            """
        )
        run(["git", "commit", "--no-verify", "--message", message], check=True)
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
        shell("git checkout -- .")
        shell(f"git checkout {previous_branch}", check=True)
        shell(f"git branch -D --force {branch_name}", check=True)


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    os.chdir("..")
    run_example_ci_configs(standalone_mode=True)
