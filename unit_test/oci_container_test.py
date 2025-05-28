import json
import os
import platform
import random
import shutil
import subprocess
import sys
import textwrap
import time
from contextlib import nullcontext
from pathlib import Path, PurePath, PurePosixPath

import pytest
import tomli_w

import cibuildwheel.oci_container
from cibuildwheel.ci import CIProvider, detect_ci_provider
from cibuildwheel.environment import EnvironmentAssignmentBash
from cibuildwheel.errors import OCIEngineTooOldError
from cibuildwheel.oci_container import (
    OCIContainer,
    OCIContainerEngineConfig,
    OCIPlatform,
    _check_engine_version,
)

# Test utilities

# for these tests we use manylinux2014 images, because they're available on
# multi architectures and include python3.8
DEFAULT_IMAGE = "quay.io/pypa/manylinux2014:2025.03.08-1"
pm = platform.machine()
DEFAULT_OCI_PLATFORM = {
    "AMD64": OCIPlatform.AMD64,
    "x86_64": OCIPlatform.AMD64,
    "ppc64le": OCIPlatform.PPC64LE,
    "s390x": OCIPlatform.S390X,
    "aarch64": OCIPlatform.ARM64,
    "arm64": OCIPlatform.ARM64,
    "ARM64": OCIPlatform.ARM64,
}[pm]

PODMAN = OCIContainerEngineConfig(name="podman")


@pytest.fixture(params=["docker", "podman"], scope="module")
def container_engine(request):
    if request.param == "docker" and not request.config.getoption("--run-docker"):
        pytest.skip("need --run-docker option to run")
    if request.param == "podman" and not request.config.getoption("--run-podman"):
        pytest.skip("need --run-podman option to run")

    def get_images() -> set[str]:
        if detect_ci_provider() is None:
            return set()
        images = subprocess.run(
            [request.param, "image", "ls", "--format", "{{json .ID}}"],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        return {json.loads(image.strip()) for image in images.splitlines() if image.strip()}

    images_before = get_images()
    try:
        yield OCIContainerEngineConfig(name=request.param)
    finally:
        images_after = get_images()
        for image in images_after - images_before:
            subprocess.run([request.param, "rmi", image], check=False)


# Tests


def test_simple(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert container.call(["echo", "hello"], capture_output=True) == "hello\n"


def test_no_lf(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert container.call(["printf", "hello"], capture_output=True) == "hello"


def test_debug_info(container_engine):
    container = OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    )
    print(container.debug_info())
    with container:
        pass


def test_environment(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert (
            container.call(
                ["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "1"}, capture_output=True
            )
            == "1\n"
        )


def test_environment_pass(container_engine, monkeypatch):
    monkeypatch.setenv("CIBUILDWHEEL", "1")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1489957071")
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert container.call(["sh", "-c", "echo $CIBUILDWHEEL"], capture_output=True) == "1\n"
        assert (
            container.call(["sh", "-c", "echo $SOURCE_DATE_EPOCH"], capture_output=True)
            == "1489957071\n"
        )


def test_cwd(container_engine):
    with OCIContainer(
        engine=container_engine,
        image=DEFAULT_IMAGE,
        oci_platform=DEFAULT_OCI_PLATFORM,
        cwd="/cibuildwheel/working_directory",
    ) as container:
        assert container.call(["pwd"], capture_output=True) == "/cibuildwheel/working_directory\n"
        assert container.call(["pwd"], capture_output=True, cwd="/opt") == "/opt\n"


def test_container_removed(container_engine):
    # test is flaky on some platforms, implement retry for 5 second
    timeout = 50  # * 100 ms = 5s
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert container.name is not None
        container_name = container.name
        for _ in range(timeout):
            docker_containers_listing = subprocess.run(
                f"{container.engine.name} container ls",
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            if container_name in docker_containers_listing:
                break
            time.sleep(0.1)
        assert container_name in docker_containers_listing

    for _ in range(timeout):
        docker_containers_listing = subprocess.run(
            f"{container.engine.name} container ls",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        if container_name not in docker_containers_listing:
            break
        time.sleep(0.1)
    assert container_name not in docker_containers_listing


def test_large_environment(container_engine):
    # max environment variable size is 128kB
    long_env_var_length = 127 * 1024
    large_environment = {
        "a": "0" * long_env_var_length,
        "b": "0" * long_env_var_length,
        "c": "0" * long_env_var_length,
        "d": "0" * long_env_var_length,
    }

    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        # check the length of d
        assert (
            container.call(["sh", "-c", "echo ${#d}"], env=large_environment, capture_output=True)
            == f"{long_env_var_length}\n"
        )


def test_binary_output(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
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


@pytest.mark.parametrize(
    "file_path",
    ["test.dat", "path/to/test.dat"],
)
def test_file_operation(
    tmp_path: Path, container_engine: OCIContainerEngineConfig, file_path: str
) -> None:
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        # test copying a file in
        test_binary_data = bytes(random.randrange(256) for _ in range(1000))
        original_test_file = tmp_path / file_path
        original_test_file.parent.mkdir(parents=True, exist_ok=True)
        original_test_file.write_bytes(test_binary_data)

        dst_file = PurePath("/tmp") / file_path

        container.copy_into(original_test_file, dst_file)

        owner = container.call(["stat", "-c", "%u:%g", dst_file], capture_output=True).strip()
        assert owner == "0:0"

        output = container.call(["cat", dst_file], capture_output=True)
        assert test_binary_data == bytes(output, encoding="utf8", errors="surrogateescape")


def test_dir_operations(tmp_path: Path, container_engine: OCIContainerEngineConfig) -> None:
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
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

        owner = container.call(["stat", "-c", "%u:%g", dst_dir], capture_output=True).strip()
        assert owner == "0:0"

        owner = container.call(["stat", "-c", "%u:%g", dst_file], capture_output=True).strip()
        assert owner == "0:0"

        output = container.call(["cat", dst_file], capture_output=True)
        assert test_binary_data == bytes(output, encoding="utf8", errors="surrogateescape")

        # test glob
        assert container.glob(dst_dir, "*.dat") == [dst_file]

        # test copy dir out
        new_test_dir = tmp_path / "test_dir_new"
        container.copy_out(dst_dir, new_test_dir)

        assert os.getuid() == new_test_dir.stat().st_uid
        assert os.getgid() == new_test_dir.stat().st_gid
        assert os.getuid() == (new_test_dir / "test.dat").stat().st_uid
        assert os.getgid() == (new_test_dir / "test.dat").stat().st_gid

        assert test_binary_data == (new_test_dir / "test.dat").read_bytes()


def test_environment_executor(container_engine: OCIContainerEngineConfig) -> None:
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assignment = EnvironmentAssignmentBash("TEST=$(echo 42)")
        assert assignment.evaluated_value({}, container.environment_executor) == "42"


def test_podman_vfs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, container_engine: OCIContainerEngineConfig
) -> None:
    if container_engine.name != "podman":
        pytest.skip("only runs with podman")
    if sys.platform.startswith("darwin"):
        pytest.skip("Skipping test because podman on this platform does not support vfs")

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

    with OCIContainer(
        engine=PODMAN, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
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


def test_create_args_volume(tmp_path: Path, container_engine: OCIContainerEngineConfig) -> None:
    if container_engine.name != "docker":
        pytest.skip("only runs with docker")

    if "CIRCLECI" in os.environ or "GITLAB_CI" in os.environ:
        pytest.skip(
            "Skipping test on CircleCI/GitLab because docker there does not support --volume"
        )

    test_mount_dir = tmp_path / "test_mount"
    test_mount_dir.mkdir()
    (test_mount_dir / "test_file.txt").write_text("1234")
    container_engine = OCIContainerEngineConfig(
        name="docker", create_args=(f"--volume={test_mount_dir}:/test_mount",)
    )

    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        assert container.call(["cat", "/test_mount/test_file.txt"], capture_output=True) == "1234"


@pytest.mark.parametrize(
    ("config", "name", "create_args"),
    [
        (
            "docker",
            "docker",
            (),
        ),
        (
            "docker;create_args:",
            "docker",
            (),
        ),
        (
            "docker;create_args:--abc --def",
            "docker",
            ("--abc", "--def"),
        ),
        (
            "docker; create_args: --abc --def",
            "docker",
            ("--abc", "--def"),
        ),
        (
            "name:docker; create_args: --abc --def",
            "docker",
            ("--abc", "--def"),
        ),
        (
            'docker; create_args: --some-option="value with spaces"',
            "docker",
            ("--some-option=value with spaces",),
        ),
        (
            'docker; create_args: --some-option="value; with; semicolons" --another-option',
            "docker",
            ("--some-option=value; with; semicolons", "--another-option"),
        ),
        (
            "docker; create_args: --platform=linux/amd64",
            "docker",
            (),
        ),
        (
            "podman; create_args: --platform=linux/amd64",
            "podman",
            (),
        ),
        (
            "docker; create_args: --platform linux/amd64",
            "docker",
            (),
        ),
        (
            "podman; create_args: --platform linux/amd64",
            "podman",
            (),
        ),
    ],
)
def test_parse_engine_config(config, name, create_args, capsys):
    engine_config = OCIContainerEngineConfig.from_config_string(config)
    assert engine_config.name == name
    assert engine_config.create_args == create_args
    if "--platform" in config:
        captured = capsys.readouterr()
        assert (
            "Using '--platform' in 'container-engine::create_args' is deprecated. It will be ignored."
            in captured.err
        )


@pytest.mark.skipif(pm != "x86_64", reason="Only runs on x86_64")
def test_enforce_32_bit(container_engine):
    with OCIContainer(
        engine=container_engine, image=DEFAULT_IMAGE, oci_platform=OCIPlatform.i386
    ) as container:
        assert container.call(["uname", "-m"], capture_output=True).strip() == "i686"
        container_args = subprocess.run(
            f"{container.engine.name} inspect -f '{{{{json .Args }}}}' {container.name}",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout
        assert json.loads(container_args) == ["/bin/bash"]


@pytest.mark.parametrize(
    ("config", "should_have_host_mount"),
    [
        ("{name}", True),
        ("{name}; disable_host_mount: false", True),
        ("{name}; disable_host_mount: true", False),
    ],
)
def test_disable_host_mount(
    tmp_path: Path,
    container_engine: OCIContainerEngineConfig,
    config: str,
    should_have_host_mount: bool,
) -> None:
    if detect_ci_provider() in {CIProvider.circle_ci, CIProvider.gitlab}:
        pytest.skip("Skipping test because docker on this platform does not support host mounts")
    if sys.platform.startswith("darwin"):
        pytest.skip("Skipping test because docker on this platform does not support host mounts")

    engine = OCIContainerEngineConfig.from_config_string(config.format(name=container_engine.name))

    sentinel_file = tmp_path / "sentinel"
    sentinel_file.write_text("12345")

    with OCIContainer(
        engine=engine, image=DEFAULT_IMAGE, oci_platform=DEFAULT_OCI_PLATFORM
    ) as container:
        host_mount_path = "/host" + str(sentinel_file)
        if should_have_host_mount:
            assert container.call(["cat", host_mount_path], capture_output=True) == "12345"
        else:
            with pytest.raises(subprocess.CalledProcessError):
                container.call(["cat", host_mount_path], capture_output=True)


@pytest.mark.parametrize("platform", list(OCIPlatform))
def test_local_image(
    container_engine: OCIContainerEngineConfig, platform: OCIPlatform, tmp_path: Path
) -> None:
    if (
        detect_ci_provider() == CIProvider.travis_ci
        and pm != "x86_64"
        and platform != DEFAULT_OCI_PLATFORM
    ):
        pytest.skip("Skipping test because docker on this platform does not support QEMU")
    if container_engine.name == "podman" and platform == OCIPlatform.ARMV7:
        # both GHA & local macOS arm64 podman desktop are failing
        pytest.xfail("podman fails with armv7l images")

    remote_image = "debian:trixie-slim"
    platform_name = platform.value.replace("/", "_")
    local_image = f"cibw_{container_engine.name}_{platform_name}_local:latest"
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(f"FROM {remote_image}")
    subprocess.run(
        [container_engine.name, "pull", f"--platform={platform.value}", remote_image],
        check=True,
    )
    subprocess.run(
        [container_engine.name, "build", f"--platform={platform.value}", "-t", local_image, "."],
        check=True,
        cwd=tmp_path,
    )
    with OCIContainer(engine=container_engine, image=local_image, oci_platform=platform):
        pass


@pytest.mark.parametrize("platform", list(OCIPlatform))
def test_multiarch_image(container_engine, platform):
    if (
        detect_ci_provider() == CIProvider.travis_ci
        and pm != "x86_64"
        and platform != DEFAULT_OCI_PLATFORM
    ):
        pytest.skip("Skipping test because docker on this platform does not support QEMU")
    if container_engine.name == "podman" and platform == OCIPlatform.ARMV7:
        # both GHA & local macOS arm64 podman desktop are failing
        pytest.xfail("podman fails with armv7l images")
    with OCIContainer(
        engine=container_engine, image="debian:trixie-slim", oci_platform=platform
    ) as container:
        output = container.call(["uname", "-m"], capture_output=True)
        output_map_kernel = {
            OCIPlatform.i386: ("i686",),
            OCIPlatform.AMD64: ("x86_64",),
            OCIPlatform.ARMV7: ("armv7l", "armv8l"),
            OCIPlatform.ARM64: ("aarch64",),
            OCIPlatform.PPC64LE: ("ppc64le",),
            OCIPlatform.RISCV64: ("riscv64",),
            OCIPlatform.S390X: ("s390x",),
        }
        assert output.strip() in output_map_kernel[platform]
        output = container.call(["dpkg", "--print-architecture"], capture_output=True)
        output_map_dpkg = {
            OCIPlatform.i386: "i386",
            OCIPlatform.AMD64: "amd64",
            OCIPlatform.ARMV7: "armhf",
            OCIPlatform.ARM64: "arm64",
            OCIPlatform.PPC64LE: "ppc64el",
            OCIPlatform.RISCV64: "riscv64",
            OCIPlatform.S390X: "s390x",
        }
        assert output_map_dpkg[platform] == output.strip()


@pytest.mark.parametrize(
    ("engine_name", "version", "context"),
    [
        (
            "docker",
            None,  # 17.12.1-ce does supports "docker version --format '{{json . }}'" so a version before that
            pytest.raises(OCIEngineTooOldError),
        ),
        (
            "docker",
            '{"Client":{"Version":"19.03.15","ApiVersion": "1.40"},"Server":{"ApiVersion": "1.40"}}',
            pytest.raises(OCIEngineTooOldError),
        ),
        (
            "docker",
            '{"Client":{"Version":"20.10.0","ApiVersion":"1.41"},"Server":{"ApiVersion":"1.41"}}',
            nullcontext(),
        ),
        (
            "docker",
            '{"Client":{"Version":"24.0.0","ApiVersion":"1.43"},"Server":{"ApiVersion":"1.43"}}',
            nullcontext(),
        ),
        (
            "docker",
            '{"Client":{"ApiVersion":"1.43"},"Server":{"ApiVersion":"1.30"}}',
            pytest.raises(OCIEngineTooOldError),
        ),
        (
            "docker",
            '{"Client":{"ApiVersion":"1.30"},"Server":{"ApiVersion":"1.43"}}',
            pytest.raises(OCIEngineTooOldError),
        ),
        ("podman", '{"Client":{"Version":"5.2.0"},"Server":{"Version":"5.1.2"}}', nullcontext()),
        ("podman", '{"Client":{"Version":"4.9.4-rhel"}}', nullcontext()),
        (
            "podman",
            '{"Client":{"Version":"5.2.0"},"Server":{"Version":"2.1.2"}}',
            pytest.raises(OCIEngineTooOldError),
        ),
        (
            "podman",
            '{"Client":{"Version":"2.2.0"},"Server":{"Version":"5.1.2"}}',
            pytest.raises(OCIEngineTooOldError),
        ),
        ("podman", '{"Client":{"Version":"3.0~rc1-rhel"}}', nullcontext()),
        ("podman", '{"Client":{"Version":"2.1.0~rc1"}}', pytest.raises(OCIEngineTooOldError)),
    ],
)
def test_engine_version(engine_name, version, context, monkeypatch):
    def mockcall(*args, **kwargs):
        if version is None:
            raise subprocess.CalledProcessError(1, " ".join(str(arg) for arg in args))
        return version

    monkeypatch.setattr(cibuildwheel.oci_container, "call", mockcall)
    engine = OCIContainerEngineConfig.from_config_string(engine_name)
    with context:
        _check_engine_version(engine)
