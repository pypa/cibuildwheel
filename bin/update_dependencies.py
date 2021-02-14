#!/usr/bin/env python3

import configparser
import os
import shutil
import subprocess
import sys
from collections import namedtuple

import requests

os.chdir(os.path.dirname(__file__))
os.chdir('..')

# CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
# regenerate the constraints files
os.environ['CUSTOM_COMPILE_COMMAND'] = "bin/update_dependencies.py"

PYTHON_VERSIONS = ['27', '35', '36', '37', '38', '39']

if '--no-docker' in sys.argv:
    for python_version in PYTHON_VERSIONS:
        subprocess.run([
            f'./env{python_version}/bin/pip-compile',
            '--allow-unsafe',
            '--upgrade',
            'cibuildwheel/resources/constraints.in',
            '--output-file', f'cibuildwheel/resources/constraints-python{python_version}.txt'
        ], check=True)
else:
    # latest manylinux2010 image with cpython 2.7 support
    image_runner = 'quay.io/pypa/manylinux2010_x86_64:2021-02-06-3d322a5'
    subprocess.run(['docker', 'pull', image_runner], check=True)
    for python_version in PYTHON_VERSIONS:
        abi_flags = '' if int(python_version) >= 38 else 'm'
        python_path = f'/opt/python/cp{python_version}-cp{python_version}{abi_flags}/bin/'
        subprocess.run([
            'docker', 'run', '--rm',
            '-e', 'CUSTOM_COMPILE_COMMAND',
            '-v', f'{os.getcwd()}:/volume',
            '--workdir', '/volume', image_runner,
            'bash', '-c',
            f'{python_path}pip install pip-tools &&'
            f'{python_path}pip-compile --allow-unsafe --upgrade '
            'cibuildwheel/resources/constraints.in '
            f'--output-file cibuildwheel/resources/constraints-python{python_version}.txt'
        ], check=True)

# default constraints.txt
shutil.copyfile(f'cibuildwheel/resources/constraints-python{PYTHON_VERSIONS[-1]}.txt', 'cibuildwheel/resources/constraints.txt')

Image = namedtuple('Image', [
    'manylinux_version',
    'platform',
    'image_name',
    'tag',
])

images = [
    Image('manylinux1', 'x86_64', 'quay.io/pypa/manylinux1_x86_64', None),
    Image('manylinux1', 'i686', 'quay.io/pypa/manylinux1_i686', None),

    # Images for manylinux2010 are pinned to the latest tag supporting cp27
    Image('manylinux2010', 'x86_64', 'quay.io/pypa/manylinux2010_x86_64', '2021-02-06-3d322a5'),
    Image('manylinux2010', 'i686', 'quay.io/pypa/manylinux2010_i686', '2021-02-06-3d322a5'),

    Image('manylinux2010', 'pypy_x86_64', 'pypywheels/manylinux2010-pypy_x86_64', None),

    Image('manylinux2014', 'x86_64', 'quay.io/pypa/manylinux2014_x86_64', None),
    Image('manylinux2014', 'i686', 'quay.io/pypa/manylinux2014_i686', None),
    Image('manylinux2014', 'aarch64', 'quay.io/pypa/manylinux2014_aarch64', None),
    Image('manylinux2014', 'ppc64le', 'quay.io/pypa/manylinux2014_ppc64le', None),
    Image('manylinux2014', 's390x', 'quay.io/pypa/manylinux2014_s390x', None),

    Image('manylinux_2_24', 'x86_64', 'quay.io/pypa/manylinux_2_24_x86_64', None),
    Image('manylinux_2_24', 'i686', 'quay.io/pypa/manylinux_2_24_i686', None),
    Image('manylinux_2_24', 'aarch64', 'quay.io/pypa/manylinux_2_24_aarch64', None),
    Image('manylinux_2_24', 'ppc64le', 'quay.io/pypa/manylinux_2_24_ppc64le', None),
    Image('manylinux_2_24', 's390x', 'quay.io/pypa/manylinux_2_24_s390x', None),
]

config = configparser.ConfigParser()

for image in images:
    # get the tag name whose digest matches 'latest'
    if image.tag is not None:
        # image has been pinned, do not update
        tag_name = image.tag
    elif image.image_name.startswith('quay.io/'):
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
