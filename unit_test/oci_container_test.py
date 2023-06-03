from __future__ import annotations

import os
import platform
import random
import shutil
import subprocess
import textwrap
from pathlib import Path, PurePath, PurePosixPath

import pytest
import tomli_w

from cibuildwheel.environment import EnvironmentAssignmentBash
from cibuildwheel.oci_container import OCIContainer, OCIContainerEngineConfig

# Test utilities

# for these tests we use manylinux2014 images, because they're available on
# multi architectures and include python3.8
pm = platform.machine()
if pm == "x86_64":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_x86_64:2020-05-17-2f8ac3b"
elif pm in {"aarch64", "arm64"}:
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_aarch64:2020-05-17-2f8ac3b"
elif pm == "ppc64le":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_ppc64le:2020-05-17-2f8ac3b"
elif pm == "s390x":
    DEFAULT_IMAGE = "quay.io/pypa/manylinux2014_s390x:2020-05-17-2f8ac3b"
else:
    DEFAULT_IMAGE = ""

PODMAN = OCIContainerEngineConfig(name="podman")


@pytest.fixture(params=["docker", "podman"])
def container_engine(request):
    if request.param == "docker" and not request.config.getoption("--run-docker"):
        pytest.skip("need --run-docker option to run")
    if request.param == "podman" and not request.config.getoption("--run-podman"):
        pytest.skip("need --run-podman option to run")
    return OCIContainerEngineConfig(name=request.param)


# Tests


def test_simple(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        assert container.call(["echo", "hello"], capture_output=True) == "hello\n"


def test_no_lf(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        assert container.call(["printf", "hello"], capture_output=True) == "hello"


def test_debug_info(container_engine):
    container = OCIContainer(engine=container_engine, image=DEFAULT_IMAGE)
    print(container.debug_info())
    with container:
        pass


def test_environment(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        assert (
            container.call(
                ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "1"}, capture_output=True
            )
            == "1\n"
        )


def test_cwd(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, cwd="/cibuildwheel/working_directory"
    ) as container:
        assert container.call(["pwd"], capture_output=True) == "/cibuildwheel/working_directory\n"
        assert container.call(["pwd"], capture_output=True, cwd="/opt") == "/opt\n"


def test_container_removed(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        docker_containers_listing = subprocess.run(
            f"{container.engine.name} container ls",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        assert container.name is not None
        assert container.name in docker_containers_listing
        old_container_name = container.name

    docker_containers_listing = subprocess.run(
        f"{container.engine.name} container ls",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
    assert old_container_name not in docker_containers_listing


def test_large_environment(container_engine):
    # max environment variable size is 128kB
    long_env_var_length = 127 * 1024
    large_environment = {
        "a": "0" * long_env_var_length,
        "b": "0" * long_env_var_length,
        "c": "0" * long_env_var_length,
        "d": "0" * long_env_var_length,
    }

    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        # check the length of d
        assert (
            container.call(["sh", "-c", "echo ${#d}"], env=large_environment, capture_output=True)
            == f"{long_env_var_length}\n"
        )


def test_binary_output(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
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


def test_file_operation(tmp_path: Path, container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        # test copying a file in
        test_binary_data = bytes(random.randrange(256) for _ in range(1000))
        original_test_file = tmp_path / "test.dat"
        original_test_file.write_bytes(test_binary_data)

        dst_file = PurePath("/tmp/test.dat")

        container.copy_into(original_test_file, dst_file)

        output = container.call(["cat", dst_file], capture_output=True)
        assert test_binary_data == bytes(output, encoding="utf8", errors="surrogateescape")


def test_dir_operations(tmp_path: Path, container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
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


def test_environment_executor(container_engine):
    with OCIContainer(engine=container_engine, image=DEFAULT_IMAGE) as container:
        assignment = EnvironmentAssignmentBash("TEST=$(echo 42)")
        assert assignment.evaluated_value({}, container.environment_executor) == "42"


def test_podman_vfs(tmp_path: Path, monkeypatch, request):
    # Tests podman VFS, for the podman in docker use-case
    if not request.config.getoption("--run-podman"):
        pytest.skip("need --run-podman option to run")

    # create the VFS configuration
    vfs_path = tmp_path / "podman_vfs"
    vfs_path.mkdir()

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
    storage_root = vfs_path / ".local/share/containers/vfs-storage"
    run_root = vfs_path / ".local/share/containers/vfs-runroot"
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

    vfs_containers_conf_fpath = vfs_path / "temp_vfs_containers.conf"
    vfs_containers_storage_conf_fpath = vfs_path / "temp_vfs_containers_storage.conf"
    with open(vfs_containers_conf_fpath, "wb") as file:
        tomli_w.dump(vfs_containers_conf_data, file)

    with open(vfs_containers_storage_conf_fpath, "wb") as file:
        tomli_w.dump(vfs_containers_storage_conf_data, file)

    monkeypatch.setenv("CONTAINERS_CONF", str(vfs_containers_conf_fpath))
    monkeypatch.setenv("CONTAINERS_STORAGE_CONF", str(vfs_containers_storage_conf_fpath))

    with OCIContainer(engine=PODMAN, image=DEFAULT_IMAGE) as container:
        # test running a command
        assert container.call(["echo", "hello"], capture_output=True) == "hello\n"

        # test copying a file into the container
        (tmp_path / "some_file.txt").write_text("1234")
        container.copy_into(tmp_path / "some_file.txt", PurePosixPath("some_file.txt"))
        assert container.call(["cat", "some_file.txt"], capture_output=True) == "1234"

    # Clean up

    # When using the VFS, user is not given write permissions by default in
    # new directories. As a workaround we use 'podman unshare' to delete them
    # as UID 0. The reason why permission errors occur on podman is documented
    # in https://podman.io/blogs/2018/10/03/podman-remove-content-homedir.html
    subprocess.run(["podman", "unshare", "rm", "-rf", vfs_path], check=True)


def test_create_args_volume(tmp_path: Path, request):
    if not request.config.getoption("--run-docker"):
        pytest.skip("need --run-docker option to run")

    if "CIRCLECI" in os.environ or "GITLAB_CI" in os.environ:
        pytest.skip(
            "Skipping test on CircleCI/GitLab because docker there does not support --volume"
        )

    test_mount_dir = tmp_path / "test_mount"
    test_mount_dir.mkdir()
    (test_mount_dir / "test_file.txt").write_text("1234")
    container_engine = OCIContainerEngineConfig(
        name="docker", create_args=[f"--volume={test_mount_dir}:/test_mount"]
    )

    with OCIContainer(
        engine=container_engine,
        image=DEFAULT_IMAGE,
    ) as container:
        assert container.call(["cat", "/test_mount/test_file.txt"], capture_output=True) == "1234"


@pytest.mark.parametrize(
    ("config", "name", "create_args"),
    [
        (
            "docker",
            "docker",
            [],
        ),
        (
            "docker;create_args:",
            "docker",
            [],
        ),
        (
            "docker;create_args:--abc --def",
            "docker",
            ["--abc", "--def"],
        ),
        (
            "docker; create_args: --abc --def",
            "docker",
            ["--abc", "--def"],
        ),
        (
            "name:docker; create_args: --abc --def",
            "docker",
            ["--abc", "--def"],
        ),
        (
            'docker; create_args: --some-option="value with spaces"',
            "docker",
            ["--some-option=value with spaces"],
        ),
        (
            'docker; create_args: --some-option="value; with; semicolons" --another-option',
            "docker",
            ["--some-option=value; with; semicolons", "--another-option"],
        ),
    ],
)
def test_parse_engine_config(config, name, create_args):
    engine_config = OCIContainerEngineConfig.from_config_string(config)
    assert engine_config.name == name
    assert engine_config.create_args == create_args
