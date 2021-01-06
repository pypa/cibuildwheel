#!/usr/bin/env python3

import glob
import os
import subprocess
import urllib.parse
from pathlib import Path

import click
from packaging.version import InvalidVersion, Version

import cibuildwheel

config = [
    # file path, version find/replace format
    ('README.md', "cibuildwheel=={}"),
    ('cibuildwheel/__init__.py', "__version__ = '{}'"),
    ('docs/faq.md', "cibuildwheel=={}"),
    ('docs/faq.md', "cibuildwheel@v{}"),
    ('docs/setup.md', "cibuildwheel@v{}"),
    ('examples/*', "cibuildwheel=={}"),
    ('setup.cfg', "version = {}"),
]


@click.command()
def bump_version():
    current_version = cibuildwheel.__version__

    try:
        commit_date_str = subprocess.run([
            'git',
            'show', '-s', '--pretty=format:%ci',
            f'v{current_version}^{{commit}}'
        ], check=True, capture_output=True, encoding='utf8').stdout
        commit_date_parts = commit_date_str.split(' ')

        url = 'https://github.com/joerick/cibuildwheel/pulls?' + urllib.parse.urlencode({
            'q': f'is:pr merged:>{commit_date_parts[0]}T{commit_date_parts[1]}{commit_date_parts[2]}',
        })
        print(f'PRs merged since last release:\n  {url}')
        print()
    except subprocess.CalledProcessError as e:
        print(e)
        print('Failed to get previous version tag information.')

    git_changes_result = subprocess.run(['git diff-index --quiet HEAD --'], shell=True)
    repo_has_uncommitted_changes = git_changes_result.returncode != 0

    if repo_has_uncommitted_changes:
        print('error: Uncommitted changes detected.')
        exit(1)

    print(              'Current version:', current_version)  # noqa
    new_version = input('    New version: ').strip()

    try:
        Version(new_version)
    except InvalidVersion:
        print("error: This version doesn't conform to PEP440")
        print('       https://www.python.org/dev/peps/pep-0440/')
        exit(1)

    actions = []

    for path_pattern, version_pattern in config:
        paths = [Path(p) for p in glob.glob(path_pattern)]

        if not paths:
            print(f'error: Pattern {path_pattern} didn’t match any files')
            exit(1)

        find_pattern = version_pattern.format(current_version)
        replace_pattern = version_pattern.format(new_version)
        found_at_least_one_file_needing_update = False

        for path in paths:
            contents = path.read_text(encoding='utf8')
            if find_pattern in contents:
                found_at_least_one_file_needing_update = True
                actions.append(
                    (path, find_pattern, replace_pattern)
                )

        if not found_at_least_one_file_needing_update:
            print(f'error: Didn’t find any occurences of “{find_pattern}” in “{path_pattern}”')
            exit(1)

    print()
    print("Here's the plan:")
    print()

    for action in actions:
        print('{}  {red}{}{off} → {green}{}{off}'.format(
            *action,
            red="\u001b[31m", green="\u001b[32m", off="\u001b[0m"
        ))

    print(f'Then commit, and tag as v{new_version}')

    answer = input('Proceed? [y/N] ').strip()

    if answer != 'y':
        print('Aborted')
        exit(1)

    for path, find, replace in actions:
        contents = path.read_text(encoding='utf8')
        contents = contents.replace(find, replace)
        path.write_text(contents, encoding='utf8')

    print('Files updated. If you want to update the changelog as part of this')
    print('commit, do that now.')
    print()

    while input('Type "done" to continue: ').strip().lower() != 'done':
        pass

    subprocess.run([
        'git', 'commit',
        '-a',
        '-m', f'Bump version: v{new_version}'
    ], check=True)

    subprocess.run([
        'git', 'tag',
        '-a',
        '-m', f'v{new_version}',
        f'v{new_version}'
    ], check=True)

    print('Done.')


if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    os.chdir('..')
    bump_version()
