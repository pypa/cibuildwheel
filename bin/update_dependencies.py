#!/usr/bin/env python3

import configparser
import os
import subprocess
from collections import namedtuple

import requests

os.chdir(os.path.dirname(__file__))
os.chdir('..')

# CUSTOM_COMPILE_COMMAND is a pip-compile option that tells users how to
# regenerate the constraints files
os.environ['CUSTOM_COMPILE_COMMAND'] = "bin/update_constraints.py"
subprocess.check_call([
    'pip-compile',
    '--allow-unsafe',
    '--upgrade',
    'cibuildwheel/resources/constraints.in',
])
for python_version in ['27', '35', '36', '37']:
    subprocess.check_call([
        f'./env{python_version}/bin/pip-compile',
        '--allow-unsafe',
        '--upgrade',
        'cibuildwheel/resources/constraints.in',
        '--output-file', f'cibuildwheel/resources/constraints-python{python_version}.txt'
    ])

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
