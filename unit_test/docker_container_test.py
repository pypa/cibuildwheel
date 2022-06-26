import atexit
import os
import platform
import random
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path, PurePath, PurePosixPath
from typing import Dict, Optional, Union

import pytest
import toml

from cibuildwheel.docker_container import DockerContainer
from cibuildwheel.environment import EnvironmentAssignmentBash

# for these tests we use manylinux2014 images, because they're available on
# multi architectures and include python3.8
pm = platform.machine()
if pm == "x86_64":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_x86_64:2020-05-17-2f8ac3b"
elif pm == "aarch64":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_aarch64:2020-05-17-2f8ac3b"
elif pm == "ppc64le":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_ppc64le:2020-05-17-2f8ac3b"
elif pm == "s390x":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_s390x:2020-05-17-2f8ac3b"
else:
    DEFAULT_IMAGE = ""

# These globals will be manipulated
temp_test_dir: Optional[tempfile.TemporaryDirectory[str]] = None
using_podman = False


# @atexit.register
def _cleanup_podman_vfs_tempdir():
    """
    Cleans up any configuration written by :func:`basis_container_kwargs`.

    For podman tests, the user is not given write permissions by default in new
    directories. As a workaround chown them before trying to delete them.

    It may be possible to handle this more cleanly in pytest itself, but using
    atexit works well enough for now.

    The reason why permission errors occur on podman is documented in
    [PodmanStoragePerms]_.

    References:
        .. [PodmanStoragePerms] https://podman.io/blogs/2018/10/03/podman-remove-content-homedir.html
    """
    global temp_test_dir
    global using_podman
    if temp_test_dir is not None:
        # When podman creates special directories, they can't be cleaned up
        # unless you fake a UID of 0. The package rootlesskit helps with that.
        if using_podman:
            subprocess.call(["podman", "unshare", "rm", "-rf", temp_test_dir.name])
    temp_test_dir = None


def basis_container_kwargs():
    """
    Generate keyword args that can be passed to to :class:`DockerContainer`.

    This is used with :func:`pytest.mark.parametrize` to run each test with
    different configurations of each supported containers engine.

    For docker we test the default configuration.

    For podman we test the default configuration and a configuration with VFS
    (virtual file system) enabled as the storage driver.

    Yields:
        Dict: a configuration passed as ``container_kwargs`` to each
        parameterized test.
    """
    global temp_test_dir
    global using_podman

    # TODO: Pytest should be aware of if we are trying to test docker / podman
    # or not
    HAVE_DOCKER = bool(shutil.which("docker"))
    HAVE_PODMAN = bool(shutil.which("podman"))

    REQUESTED_DOCKER = HAVE_DOCKER
    REQUESTED_PODMAN = HAVE_PODMAN

    if temp_test_dir is None:
        # Only setup the temp directory once for all tests
        temp_test_dir = tempfile.TemporaryDirectory(prefix="cibw_test_")
        if REQUESTED_PODMAN:
            # Register the special cleanup hook after the temp directory is
            # created to ensure that it runs before the temp directory logic
            # runs (which will not handle cases where there is a fake root
            # UID).
            atexit.register(_cleanup_podman_vfs_tempdir)

    if REQUESTED_DOCKER:
        # Basic podman configuration
        yield {"container_engine": "docker", "docker_image": DEFAULT_IMAGE}

    if REQUESTED_PODMAN:
        # Basic podman usage
        using_podman = True
        yield {"container_engine": "podman", "docker_image": DEFAULT_IMAGE}

        # VFS Podman usage (for the podman in docker use-case)
        oci_environ = _setup_podman_vfs(temp_test_dir.name)
        yield {
            "container_engine": "podman",
            "docker_image": DEFAULT_IMAGE,
            "env": oci_environ,
        }


def _setup_podman_vfs(dpath):
    """
    Setup the filesystem and environment variables for the VFS podman test
    """
    dpath = Path(dpath)
    # This requires that we write configuration files and point to them
    # with environment variables before we run podman
    # https://github.com/containers/common/blob/main/docs/containers.conf.5.md
    vfs_containers_conf_data = {
        "containers": {
            "default_capabilities": [
                "CHOWN",
                "DAC_OVERRIDE",
                "FOWNER",
                "FSETID",
                "KILL",
                "NET_BIND_SERVICE",
                "SETFCAP",
                "SETGID",
                "SETPCAP",
                "SETUID",
                "SYS_CHROOT",
            ]
        },
        "engine": {"cgroup_manager": "cgroupfs", "events_logger": "file"},
    }
    # https://github.com/containers/storage/blob/main/docs/containers-storage.conf.5.md
    storage_root = dpath / ".local/share/containers/vfs-storage"
    run_root = dpath / ".local/share/containers/vfs-runroot"
    storage_root.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)
    vfs_containers_storage_conf_data = {
        "storage": {
            "driver": "vfs",
            "graphroot": os.fspath(storage_root),
            "runroot": os.fspath(run_root),
            "rootless_storage_path": os.fspath(storage_root),
            "options": {
                # "remap-user": "containers",
                "aufs": {"mountopt": "rw"},
                "overlay": {"mountopt": "rw", "force_mask": "shared"},
                # "vfs": {"ignore_chown_errors": "true"},
            },
        }
    }
    vfs_containers_conf_fpath = dpath / "temp_vfs_containers.conf"
    vfs_containers_storage_conf_fpath = dpath / "temp_vfs_containers_storage.conf"
    with open(vfs_containers_conf_fpath, "w") as file:
        toml.dump(vfs_containers_conf_data, file)

    with open(vfs_containers_storage_conf_fpath, "w") as file:
        toml.dump(vfs_containers_storage_conf_data, file)

    oci_environ = os.environ.copy()
    oci_environ.update(
        {
            "CONTAINERS_CONF": os.fspath(vfs_containers_conf_fpath),
            "CONTAINERS_STORAGE_CONF": os.fspath(vfs_containers_storage_conf_fpath),
        }
    )
    return oci_environ


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_simple(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        assert container.call(["echo", "hello"], capture_output=True) == "hello\n"


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_no_lf(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        assert container.call(["printf", "hello"], capture_output=True) == "hello"


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_debug_info(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    container = DockerContainer(**container_kwargs)
    print(container.debug_info())
    with container:
        pass


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_environment(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        assert (
            container.call(
                ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "1"}, capture_output=True
            )
            == "1\n"
        )


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_cwd(container_kwargs):
    with DockerContainer(cwd="/cibuildwheel/working_directory", **container_kwargs) as container:
        assert container.call(["pwd"], capture_output=True) == "/cibuildwheel/working_directory\n"
        assert container.call(["pwd"], capture_output=True, cwd="/opt") == "/opt\n"


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_container_removed(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        docker_containers_listing = subprocess.run(
            f"{container.container_engine} container ls",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        ).stdout
        assert container.name is not None
        assert container.name in docker_containers_listing
        old_container_name = container.name

    docker_containers_listing = subprocess.run(
        f"{container.container_engine} container ls",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ).stdout
    assert old_container_name not in docker_containers_listing


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_large_environment(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    # max environment variable size is 128kB
    long_env_var_length = 127 * 1024
    large_environment = {
        "a": "0" * long_env_var_length,
        "b": "0" * long_env_var_length,
        "c": "0" * long_env_var_length,
        "d": "0" * long_env_var_length,
    }

    with DockerContainer(**container_kwargs) as container:
        # check the length of d
        assert (
            container.call(["sh", "-c", "echo ${#d}"], env=large_environment, capture_output=True)
            == f"{long_env_var_length}\n"
        )


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_binary_output(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        # note: the below embedded snippets are in python2

        # check that we can pass though arbitrary binary data without erroring
        container.call(
            [
                "/usr/bin/python2",
                "-c",
                textwrap.dedent(
                    """
                    import sys
                    sys.stdout.write(''.join(chr(n) for n in range(0, 256)))
                    """
                ),
            ]
        )

        # check that we can capture arbitrary binary data
        output = container.call(
            [
                "/usr/bin/python2",
                "-c",
                textwrap.dedent(
                    """
                    import sys
                    sys.stdout.write(''.join(chr(n % 256) for n in range(0, 512)))
                    """
                ),
            ],
            capture_output=True,
        )

        data = bytes(output, encoding="utf8", errors="surrogateescape")

        for i in range(512):
            assert data[i] == i % 256

        # check that environment variables can carry binary data, except null characters
        # (https://www.gnu.org/software/libc/manual/html_node/Environment-Variables.html)
        binary_data = bytes(n for n in range(1, 256))
        binary_data_string = str(binary_data, encoding="utf8", errors="surrogateescape")
        output = container.call(
            ["python2", "-c", 'import os, sys; sys.stdout.write(os.environ["TEST_VAR"])'],
            env={"TEST_VAR": binary_data_string},
            capture_output=True,
        )
        assert output == binary_data_string


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_file_operation(tmp_path: Path, container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        # test copying a file in
        test_binary_data = bytes(random.randrange(256) for _ in range(1000))
        original_test_file = tmp_path / "test.dat"
        original_test_file.write_bytes(test_binary_data)

        dst_file = PurePath("/tmp/test.dat")

        container.copy_into(original_test_file, dst_file)

        output = container.call(["cat", dst_file], capture_output=True)
        assert test_binary_data == bytes(output, encoding="utf8", errors="surrogateescape")


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_dir_operations(tmp_path: Path, container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        test_binary_data = bytes(random.randrange(256) for _ in range(1000))
        original_test_file = tmp_path / "test.dat"
        original_test_file.write_bytes(test_binary_data)

        # test copying a dir in
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        test_file = test_dir / "test.dat"
        shutil.copyfile(original_test_file, test_file)

        dst_dir = PurePosixPath("/tmp/test_dir")
        dst_file = dst_dir / "test.dat"
        container.copy_into(test_dir, dst_dir)

        output = container.call(["cat", dst_file], capture_output=True)
        assert test_binary_data == bytes(output, encoding="utf8", errors="surrogateescape")

        # test glob
        assert container.glob(dst_dir, "*.dat") == [dst_file]

        # test copy dir out
        new_test_dir = tmp_path / "test_dir_new"
        container.copy_out(dst_dir, new_test_dir)

        assert test_binary_data == (new_test_dir / "test.dat").read_bytes()


@pytest.mark.docker
@pytest.mark.parametrize("container_kwargs", basis_container_kwargs())
def test_environment_executor(container_kwargs, monkeypatch):
    for k, v in container_kwargs.pop("env", {}).items():
        monkeypatch.setenv(k, v)
    with DockerContainer(**container_kwargs) as container:
        assignment = EnvironmentAssignmentBash("TEST=$(echo 42)")
        assert assignment.evaluated_value({}, container.environment_executor) == "42"
