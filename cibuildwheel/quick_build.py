import os, subprocess, shlex, sys, shutil, re


def quick_build():
    stash_id = subprocess.check_output([
        'git', 'stash',
        'create', 
        'cibuildwheel quick-build'
    ]).strip()

    subprocess.check_call([
        'git', 'push', 
        '-f', 
        'origin', 
        '%s:refs/heads/cibuildwheel-test' % stash_id
    ])

    print('\nTest branch updated.\n')

    configured_services = []

    if os.path.exists('.travis.yml'):
        configured_services.append('travis')
    if os.path.exists('appveyor.yml') or os.path.exists('.appveyor.yml'):
        configured_services.append('appveyor')
    
    username, repo = get_github_username_and_repo()

    if username and repo:
        if 'travis' in configured_services:
            print('Travis build: https://travis-ci.org/%s/%s/branches' % (username, repo))
        if 'appveyor' in configured_services:
            print('Appveyor build: https://ci.appveyor.com/project/%s/%s' % (username, repo))
    
    print('')


def get_github_username_and_repo():
    url = subprocess.check_output([
        'git', 'remote', 'get-url', 'origin'
    ]).strip()

    if url:
        return extract_github_username_and_repo_from_url(url)

    return None, None


def extract_github_username_and_repo_from_url(remote_url):
    patterns = [
        r'https://github.com/(?P<username>.+)/(?P<repo>.+).git',
        r'git@github.com:(?P<username>.+)/(?P<repo>.+).git',
        r'git://github.com/(?P<username>.+)/(?P<repo>.+).git',
    ]

    for pattern in patterns:
        match = re.match(pattern, remote_url)

        if match:
            return match.group('username'), match.group('repo')

    return None, None
