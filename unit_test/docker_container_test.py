import subprocess
import textwrap

import pytest

from cibuildwheel.docker_container import DockerContainer

DEFAULT_IMAGE = 'centos:6'


@pytest.mark.slow
def test_simple():
    with DockerContainer(DEFAULT_IMAGE) as container:
        assert container.call(['echo', 'hello'], capture_output=True) == 'hello\n'


@pytest.mark.slow
def test_no_lf():
    with DockerContainer(DEFAULT_IMAGE) as container:
        assert container.call(['printf', 'hello'], capture_output=True) == 'hello'


@pytest.mark.slow
def test_environment():
    with DockerContainer(DEFAULT_IMAGE) as container:
        assert container.call(['sh', '-c', 'echo $TEST_VAR'], env={'TEST_VAR': '1'}, capture_output=True) == '1\n'


@pytest.mark.slow
def test_container_removed():
    with DockerContainer(DEFAULT_IMAGE) as container:
        container.call(['true'])
        docker_containers_listing = subprocess.run('docker container ls', shell=True, check=True, capture_output=True, universal_newlines=True).stdout
        assert container.name in docker_containers_listing
        old_container_name = container.name

    docker_containers_listing = subprocess.run('docker container ls', shell=True, check=True, capture_output=True, universal_newlines=True).stdout
    assert old_container_name not in docker_containers_listing


@pytest.mark.slow
def test_large_environment():
    # max environment variable size is 128kB
    long_env_var_length = 127*1024
    large_environment = {
        'a': '0'*long_env_var_length,
        'b': '0'*long_env_var_length,
        'c': '0'*long_env_var_length,
        'd': '0'*long_env_var_length,
    }

    with DockerContainer(DEFAULT_IMAGE) as container:
        # check the length of d
        assert container.call(['sh', '-c', 'echo ${#d}'], env=large_environment, capture_output=True) == f'{long_env_var_length}\n'


@pytest.mark.slow
def test_binary_output():
    with DockerContainer(DEFAULT_IMAGE) as container:
        # the centos image only has python 2.6, so the below embedded snippets
        # are in python2

        # check that we can pass though arbitrary binary data without erroring
        container.call(['/usr/bin/python2', '-c', textwrap.dedent('''
            import sys
            sys.stdout.write(''.join(chr(n) for n in range(0, 256)))
        ''')])

        # check that we can capture arbitrary binary data
        output = container.call(['/usr/bin/python2', '-c', textwrap.dedent('''
            import sys
            sys.stdout.write(''.join(chr(n % 256) for n in range(0, 512)))
        ''')], capture_output=True)

        data = bytes(output, encoding='utf8', errors='surrogateescape')

        for i in range(0, 512):
            assert data[i] == i % 256

        # check that environment variables can carry binary data, except null characters
        # (https://www.gnu.org/software/libc/manual/html_node/Environment-Variables.html)
        binary_data = bytes(n for n in range(1, 256))
        binary_data_string = str(binary_data, encoding='utf8', errors='surrogateescape')
        output = container.call(
            ['python2', '-c', 'import os, sys; sys.stdout.write(os.environ["TEST_VAR"])'],
            env={'TEST_VAR': binary_data_string},
            capture_output=True,
        )
        assert output == binary_data_string
