import os
import subprocess
from setuptools import (
    Extension,
    setup,
)

versions_output_text = subprocess.check_output(
    ['pip', 'freeze', '--all', '-qq'],
    universal_newlines=True,
)
versions = versions_output_text.strip().splitlines()

# `versions` now looks like:
# ['pip==x.x.x', 'setuptools==x.x.x', 'wheel==x.x.x']

print('Gathered versions', versions)

for package_name in ['pip', 'setuptools', 'wheel']:
    env_name = 'EXPECTED_{}_VERSION'.format(package_name.upper())
    expected_version = os.environ[env_name]

    print(package_name, 'version should equal', expected_version)

    assert '{}=={}'.format(package_name, expected_version) in versions

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
