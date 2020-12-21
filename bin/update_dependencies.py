#!/usr/bin/env python3

import configparser
import os
import shutil
import subprocess
import sys
from collections import namedtuple, defaultdict

import packaging.version
import requests

os.chdir(os.path.dirname(__file__))
os.chdir('..')

# CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
# regenerate the constraints files
os.environ['CUSTOM_COMPILE_COMMAND'] = "bin/update_dependencies.py"

PYTHON_VERSIONS = ['27', '35', '36', '37', '38', '39']

if '--no-docker' in sys.argv:
    for python_version in PYTHON_VERSIONS:
        subprocess.check_call([
            f'./env{python_version}/bin/pip-compile',
            '--allow-unsafe',
            '--upgrade',
            'cibuildwheel/resources/constraints.in',
            '--output-file', f'cibuildwheel/resources/constraints-python{python_version}.txt'
        ])
else:
    image = 'quay.io/pypa/manylinux2010_x86_64:latest'
    subprocess.check_call(['docker', 'pull', image])
    for python_version in PYTHON_VERSIONS:
        abi_flags = '' if int(python_version) >= 38 else 'm'
        python_path = f'/opt/python/cp{python_version}-cp{python_version}{abi_flags}/bin/'
        subprocess.check_call([
            'docker', 'run', '--rm',
            '-e', 'CUSTOM_COMPILE_COMMAND',
            '-v', f'{os.getcwd()}:/volume',
            '--workdir', '/volume', image,
            'bash', '-c',
            f'{python_path}pip install pip-tools &&'
            f'{python_path}pip-compile --allow-unsafe --upgrade '
            'cibuildwheel/resources/constraints.in '
            f'--output-file cibuildwheel/resources/constraints-python{python_version}.txt'
        ])

# default constraints.txt
shutil.copyfile(f'cibuildwheel/resources/constraints-python{PYTHON_VERSIONS[-1]}.txt', 'cibuildwheel/resources/constraints.txt')

Image = namedtuple('Image', [
    'manylinux_version',
    'platform',
    'image_name',
])

images = [
    Image('manylinux1', 'x86_64', 'quay.io/pypa/manylinux1_x86_64'),
    Image('manylinux1', 'i686', 'quay.io/pypa/manylinux1_i686'),

    Image('manylinux2010', 'x86_64', 'quay.io/pypa/manylinux2010_x86_64'),
    Image('manylinux2010', 'i686', 'quay.io/pypa/manylinux2010_i686'),
    Image('manylinux2010', 'pypy_x86_64', 'pypywheels/manylinux2010-pypy_x86_64'),

    Image('manylinux2014', 'x86_64', 'quay.io/pypa/manylinux2014_x86_64'),
    Image('manylinux2014', 'i686', 'quay.io/pypa/manylinux2014_i686'),
    Image('manylinux2014', 'aarch64', 'quay.io/pypa/manylinux2014_aarch64'),
    Image('manylinux2014', 'ppc64le', 'quay.io/pypa/manylinux2014_ppc64le'),
    Image('manylinux2014', 's390x', 'quay.io/pypa/manylinux2014_s390x'),
]

config = configparser.ConfigParser()

for image in images:
    # get the tag name whose digest matches 'latest'
    if image.image_name.startswith('quay.io/'):
        _, _, repository_name = image.image_name.partition('/')
        response = requests.get(
            f'https://quay.io/api/v1/repository/{repository_name}?includeTags=true'
        )
        response.raise_for_status()
        repo_info = response.json()
        tags_dict = repo_info['tags']

        latest_tag = tags_dict.pop('latest')
        # find the tag whose manifest matches 'latest'
        tag_name = next(
            name
            for (name, info) in tags_dict.items()
            if info['manifest_digest'] == latest_tag['manifest_digest']
        )
    else:
        response = requests.get(
            f'https://hub.docker.com/v2/repositories/{image.image_name}/tags'
        )
        response.raise_for_status()
        tags = response.json()['results']

        latest_tag = next(
            tag for tag in tags if tag['name'] == 'latest'
        )
        # i don't know what it would mean to have multiple images per tag
        assert len(latest_tag['images']) == 1
        digest = latest_tag['images'][0]['digest']

        pinned_tag = next(
            tag
            for tag in tags
            if tag != latest_tag and tag['images'][0]['digest'] == digest
        )
        tag_name = pinned_tag['name']

    if not config.has_section(image.platform):
        config[image.platform] = {}

    config[image.platform][image.manylinux_version] = f'{image.image_name}:{tag_name}'

with open('cibuildwheel/resources/pinned_docker_images.cfg', 'w') as f:
    config.write(f)


# update Python on windows
# CPython uses nugget
# c.f. https://docs.microsoft.com/en-us/nuget/api/overview
response = requests.get('https://api.nuget.org/v3/index.json')
response.raise_for_status()
api_info = response.json()
for resource in api_info['resources']:
    if resource['@type'] == 'PackageBaseAddress/3.0.0':
        endpoint = resource['@id']
cp_versions = {'64': [], '32': [] }
for id, package in [('64', 'python'), ('32', 'pythonx86')]:
    response = requests.get(f'{endpoint}{package}/index.json')
    response.raise_for_status()
    cp_info = response.json()
    for version_str in cp_info['versions']:
        version = packaging.version.parse(version_str)
        if version.is_devrelease:
            continue
        cp_versions[id].append(version)
    cp_versions[id].sort()
# PyPy is downloaded from https://downloads.python.org/pypy
response = requests.get('https://downloads.python.org/pypy/versions.json')
response.raise_for_status()
pp_realeases = response.json()
pp_versions = defaultdict(list)
for pp_realease in pp_realeases:
    if pp_realease['pypy_version'] == 'nightly':
        continue
    version = packaging.version.parse(pp_realease['pypy_version'])
    python_version = packaging.version.parse(pp_realease['python_version'])
    python_version = f'{python_version.major}.{python_version.minor}'
    url = None
    for file in pp_realease['files']:
        if f"{file['platform']}-{file['arch']}" == 'win32-x86':
            url = file['download_url']
            break
    if url:
        pp_versions[python_version].append((version, url))

# load windows.py
with open('cibuildwheel/windows.py', 'rt') as f:
    lines = f.readlines()
# hugly search pattern, package configuration shall probably done otherwise if we want to do this
for index, line in enumerate(lines):
    if 'PythonConfiguration' in line and 'url=None' in line and "identifier='cp3" in line:
        if "arch='32'" in line:
            id='32'
        else:
            id='64'
        start = line.index("version='") + 9
        end = line.index("'", start)
        current_version = packaging.version.parse(line[start:end])
        new_version = current_version
        max_version = packaging.version.parse(f'{current_version.major}.{current_version.minor + 1}')
        allow_prerelease = False
        if current_version.is_prerelease:
            release_version = packaging.version.parse(f'{current_version.major}.{current_version.minor}')
            if release_version in cp_versions[id]:
                new_version = release_version
            else:
                allow_prerelease = True
                max_version = release_version

        for version in cp_versions[id]:
            if version.is_prerelease and not allow_prerelease:
                continue
            if version > new_version and version < max_version:
                new_version = version
        lines[index] = line[:start] + str(new_version) + line[end:]
    elif 'PythonConfiguration' in line and "identifier='pp" in line:
        start = line.index("version='") + 9
        end = line.index("'", start)
        id = line[start:end]
        start = line.index("url='") + 5
        end = line.index("'", start)
        current_url = line[start:end]
        _, current_version_str, _ = current_url.split('/')[-1].split('-')
        current_version = packaging.version.parse(current_version_str)
        new_version = current_version
        new_url = current_url
        max_version = packaging.version.parse(f'{current_version.major}.{current_version.minor + 1}')
        allow_prerelease = False
        if current_version.is_prerelease:
            release_version = packaging.version.parse(f'{current_version.major}.{current_version.minor}')
            found_release = False
            for version, url in pp_versions[id]:
                if release_version == version:
                    new_version = release_version
                    new_url = url
                    found_release = True
                    break
            if not found_release:
                allow_prerelease = True
                max_version = release_version

        for version, url in pp_versions[id]:
            if version.is_prerelease and not allow_prerelease:
                continue
            if version > new_version and version < max_version:
                new_url = url
                new_version = version
        lines[index] = line[:start] + new_url + line[end:]

with open('cibuildwheel/windows.py', 'wt') as f:
    f.writelines(lines)


# update Python on macOS
# Cpython
# c.f. https://github.com/python/pythondotorg/issues/1352
response = requests.get('https://www.python.org/api/v2/downloads/release/?version=3&is_published=true')
response.raise_for_status()
release_info = response.json()
cp_versions = {}
for release in release_info:
    if not release['is_published']:
        continue
    parts = release['name'].split()
    if parts[0].lower() != 'python':
        continue
    assert len(parts) == 2
    version = packaging.version.parse(parts[1])
    cp_versions[release['resource_uri']] = [version]

response = requests.get('https://www.python.org/api/v2/downloads/release_file/?os=2')
response.raise_for_status()
file_info = response.json()

for file in file_info:
    key = file['release']
    if key not in cp_versions.keys():
        continue
    cp_versions[key].append(file['url'])

# PyPy is downloaded from https://downloads.python.org/pypy
response = requests.get('https://downloads.python.org/pypy/versions.json')
response.raise_for_status()
pp_realeases = response.json()
pp_versions = defaultdict(list)
for pp_realease in pp_realeases:
    if pp_realease['pypy_version'] == 'nightly':
        continue
    version = packaging.version.parse(pp_realease['pypy_version'])
    python_version = packaging.version.parse(pp_realease['python_version'])
    python_version = f'{python_version.major}.{python_version.minor}'
    url = None
    for file in pp_realease['files']:
        if f"{file['platform']}-{file['arch']}" == 'darwin-x64':
            url = file['download_url']
            break
    if url:
        pp_versions[python_version].append((version, url))

# load macos.py
with open('cibuildwheel/macos.py', 'rt') as f:
    lines = f.readlines()
# hugly search pattern, package configuration shall probably done otherwise if we want to do this
for index, line in enumerate(lines):
    if 'PythonConfiguration' in line and "identifier='cp3" in line:
        start = line.index("url='") + 5
        end = line.index("'", start)
        current_url = line[start:end]
        _, current_version_str, installer_kind = current_url.split('/')[-1].split('-')
        current_version = packaging.version.parse(current_version_str)
        new_version = current_version
        new_url = current_url
        max_version = packaging.version.parse(f'{current_version.major}.{current_version.minor + 1}')
        allow_prerelease = False
        if current_version.is_prerelease:
            release_version = packaging.version.parse(f'{current_version.major}.{current_version.minor}')
            found_release = False
            for version in cp_versions.values():
                if release_version == version[0]:
                    # find installer
                    found_url = False
                    for url in version[1:]:
                        if url.endswith(installer_kind):
                            new_url = url
                            found_url = True
                            break
                    if found_url:
                        new_version = release_version
                        found_release = True
                        break
            if not found_release:
                allow_prerelease = True
                max_version = release_version

        for version in cp_versions.values():
            if version[0].is_prerelease and not allow_prerelease:
                continue
            if version[0] > new_version and version[0] < max_version:
                # check installer kind
                for url in version[1:]:
                    if url.endswith(installer_kind):
                        new_url = url
                        new_version = version[0]
        lines[index] = line[:start] + new_url + line[end:]
    elif 'PythonConfiguration' in line and "identifier='pp" in line:
        start = line.index("version='") + 9
        end = line.index("'", start)
        id = line[start:end]
        start = line.index("url='") + 5
        end = line.index("'", start)
        current_url = line[start:end]
        _, current_version_str, _ = current_url.split('/')[-1].split('-')
        current_version = packaging.version.parse(current_version_str)
        new_version = current_version
        new_url = current_url
        max_version = packaging.version.parse(f'{current_version.major}.{current_version.minor + 1}')
        allow_prerelease = False
        if current_version.is_prerelease:
            release_version = packaging.version.parse(f'{current_version.major}.{current_version.minor}')
            found_release = False
            for version, url in pp_versions[id]:
                if release_version == version:
                    new_version = release_version
                    new_url = url
                    found_release = True
                    break
            if not found_release:
                allow_prerelease = True
                max_version = release_version

        for version, url in pp_versions[id]:
            if version.is_prerelease and not allow_prerelease:
                continue
            if version > new_version and version < max_version:
                new_url = url
                new_version = version
        lines[index] = line[:start] + new_url + line[end:]
with open('cibuildwheel/macos.py', 'wt') as f:
    f.writelines(lines)
