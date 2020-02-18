import os
import subprocess


def test_expected_pip_version():
    expected_pip_version = os.environ['EXPECTED_PIP_VERSION']

    versions_output_text = subprocess.check_output(
        ['pip', 'freeze', '--all', '-qq'],
        universal_newlines=True,
    )
    versions = versions_output_text.strip().splitlines()

    # `versions` now looks like:
    # ['pip==x.x.x', 'setuptools==x.x.x', 'wheel==x.x.x']

    assert 'pip=={}'.format(expected_pip_version) in versions
