import os
import subprocess
import sys
import textwrap
from pathlib import Path, PurePath
from typing import Dict, List, NamedTuple, Optional, Set

from .architecture import Architecture
from .docker_container import DockerContainer
from .logger import log
from .typing import PathOrStr
from .util import (
    BuildOptions,
    BuildSelector,
    NonPlatformWheelError,
    get_build_verbosity_extra_flags,
    prepare_command,
    read_python_configs,
)

# Toolchains to compile native code for different architectures
toolchains = {"aarch64": "/aarch64-unknown-linux-gnueabi/"}


def platform_tag_to_arch(platform_tag: str) -> str:
    return platform_tag.replace("manylinux_", "")


# Setup environment to prepare the toolchain
class TargetArchEnvUtil:
    def __init__(
        self,
        cross_root: Optional[str] = None,
        target_arch: Optional[str] = None,
    ):
        assert cross_root is not None
        assert target_arch is not None
        self.tmp = "/tmp"
        self.host = "/host"
        self.deps = "/install_deps"
        self.host_machine_tmp_in_container = self.host + self.tmp
        self.host_machine_deps_in_container = self.host_machine_tmp_in_container + self.deps
        self.host_machine_deps_usr_in_container = (
            self.host_machine_tmp_in_container + self.deps + "/usr"
        )
        self.host_machine_deps_usr_out_container = self.tmp + self.deps + "/usr"
        self.toolchain_deps = cross_root + toolchains[target_arch]


# Install the dependencies into the toolchain
def execute_cmd(
    docker: DockerContainer,
    native_docker_image: str,
    cmd_str: str,
    before_build: bool,
    target_arch: str,
    env: Optional[Dict[str, str]] = None,
) -> None:
    invalid_cmd = False
    pip_install_env_create = True
    tmpdirpath = ""

    assert env is not None
    target_arch_env = TargetArchEnvUtil(env.get("CROSS_ROOT"), target_arch)

    cmds = [cmd.strip().replace("\t", " ") for cmd in cmd_str.split("&&")]

    # Copy install_deps.sh script from container's tmp to host machine tmp and use it
    if not os.path.isfile(f"{target_arch_env.tmp}/install_deps.sh"):
        docker.call(
            [
                "cp",
                f"{target_arch_env.tmp}/install_deps.sh",
                target_arch_env.host_machine_tmp_in_container,
            ]
        )

    for cmd in cmds:
        if cmd.startswith("yum "):
            # Install the dependencies into the emulated docker container and
            # Copy back the installed files into host machine
            print(
                "\nRunning cmd: '"
                + cmd
                + "' in target's native container '"
                + native_docker_image
                + "' and copy the artifacts into the toolchain\n"
            )

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--volume=/:/host",  # ignored on CircleCI
                    native_docker_image,
                    "bash",
                    "-c",
                    f'{target_arch_env.host_machine_tmp_in_container}/install_deps.sh "{cmd}"',
                ],
                check=True,
            )

            # The installed dependencies are in /tmp/install_deps on host machine.
            # Copy them into the toolchain
            dir_list = os.listdir(target_arch_env.host_machine_deps_usr_out_container)
            for dir in dir_list:
                docker.call(
                    [
                        "cp",
                        "-rf",
                        f"{target_arch_env.host_machine_deps_usr_in_container}/{dir}",
                        target_arch_env.toolchain_deps,
                    ]
                )
        elif cmd.startswith("pip ") or cmd.startswith("python ") or cmd.startswith("python3 "):
            if pip_install_env_create and before_build:
                tmpdirpath = docker.call(["mktemp", "-d"], capture_output=True).strip()
                # Adding temp directory in PATH
                env_path_var = env.get("PATH")
                env_path_var = f"{tmpdirpath}:{env_path_var}"
                temp_dict = {"PATH": env_path_var}
                env.update(temp_dict)

                build_pip = docker.call(
                    ["which", "build-pip"], env=env, capture_output=True
                ).strip()
                build_pybin = build_pip[: build_pip.rindex("/")]

                docker.call(["ln", "-s", build_pip, tmpdirpath + "/pip"], env=env)
                docker.call(
                    ["ln", "-s", f"{build_pybin}/build-pip3", f"{tmpdirpath}/pip3"], env=env
                )
                docker.call(
                    ["ln", "-s", f"{build_pybin}/build-python", f"{tmpdirpath}/python"], env=env
                )
                docker.call(
                    ["ln", "-s", f"{build_pybin}/build-python3", f"{tmpdirpath}/python3"], env=env
                )

                pip_install_env_create = False
            docker.call(["sh", "-c", cmd], env=env)
        else:
            print(
                "During cross compilation, in wheel build phase, only pip/python/yum related commands are allowed"
            )
            invalid_cmd = True
            break
    docker.call(["rm", "-rf", tmpdirpath])

    if invalid_cmd is True:
        sys.exit(1)


class PythonConfiguration(NamedTuple):
    version: str
    identifier: str
    path_str: str

    @property
    def path(self) -> PurePath:
        return PurePath(self.path_str)


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> List[PythonConfiguration]:

    full_python_configs = read_python_configs("crosslinux")
    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    # return all configurations whose arch is in our `architectures` set,
    # and match the build/skip rules
    return [
        c
        for c in python_configurations
        if any(c.identifier.endswith(arch.value) for arch in architectures)
        and build_selector(c.identifier)
    ]


def build(options: BuildOptions) -> None:
    try:
        # check docker is installed
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.DEVNULL)
    except Exception:
        print(
            "cibuildwheel: Docker not found. Docker is required to run Linux builds. "
            "If you're building on Travis CI, add `services: [docker]` to your .travis.yml."
            "If you're building on Circle CI in Linux, add a `setup_remote_docker` step to your .circleci/config.yml",
            file=sys.stderr,
        )
        sys.exit(2)

    assert options.manylinux_images is not None
    python_configurations = get_python_configurations(options.build_selector, options.architectures)
    platforms = [
        ("cp", "manylinux_aarch64", options.manylinux_images["cross_aarch64"]),
    ]

    cwd = Path.cwd()
    abs_package_dir = options.package_dir.resolve()
    if cwd != abs_package_dir and cwd not in abs_package_dir.parents:
        raise Exception("package_dir must be inside the working directory")

    container_project_path = PurePath("/project")
    container_package_dir = container_project_path / abs_package_dir.relative_to(cwd)
    container_output_dir = PurePath("/output")

    for implementation, platform_tag, docker_image in platforms:
        platform_configs = [
            c
            for c in python_configurations
            if c.identifier.startswith(implementation) and c.identifier.endswith(platform_tag)
        ]
        if not platform_configs:
            continue

        try:
            log.step(f"Starting Docker image {docker_image}...")
            with DockerContainer(
                docker_image,
                simulate_32_bit=platform_tag.endswith("i686"),
                cwd=container_project_path,
            ) as docker:

                log.step("Copying project into Docker...")
                docker.copy_into(Path.cwd(), container_project_path)
                target_arch = platform_tag_to_arch(platform_tag)

                if options.before_all:
                    log.step("Running before_all...")

                    env = docker.get_environment()
                    env["PATH"] = f'/opt/python/cp38-cp38/bin:{env["PATH"]}'
                    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
                    env = options.environment.as_dictionary(
                        env, executor=docker.environment_executor
                    )

                    before_all_prepared = prepare_command(
                        options.before_all,
                        project=container_project_path,
                        package=container_package_dir,
                    )

                    execute_cmd(
                        docker=docker,
                        native_docker_image=options.manylinux_images[target_arch],
                        cmd_str=before_all_prepared,
                        before_build=False,
                        target_arch=target_arch,
                        env=env,
                    )
                for config in platform_configs:

                    log.build_start(config.identifier)

                    dependency_constraint_flags: List[PathOrStr] = []

                    if options.dependency_constraints:
                        constraints_file = options.dependency_constraints.get_for_python_version(
                            config.version
                        )
                        container_constraints_file = PurePath("/constraints.txt")

                        docker.copy_into(constraints_file, container_constraints_file)
                        dependency_constraint_flags = ["-c", container_constraints_file]

                    log.step("Setting up build environment...")

                    env = docker.get_environment()

                    # put this config's python top of the list
                    python_bin = config.path / "bin"
                    env["PATH"] = f'{python_bin}:{env["PATH"]}'
                    cross_py = str(config.path)
                    build_py = cross_py[: cross_py.rindex("/")]
                    build_py_bin = f"{build_py}/bin"
                    env["PATH"] = f"{build_py_bin}:{env['PATH']}"

                    env = options.environment.as_dictionary(
                        env, executor=docker.environment_executor
                    )

                    # check config python is still on PATH
                    which_python = docker.call(
                        ["which", "python"], env=env, capture_output=True
                    ).strip()
                    if PurePath(which_python) != python_bin / "python":
                        print(
                            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                    which_pip = docker.call(["which", "pip"], env=env, capture_output=True).strip()
                    if PurePath(which_pip) != python_bin / "pip":
                        print(
                            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                    if options.before_build:
                        log.step("Running before_build...")
                        before_build_prepared = prepare_command(
                            options.before_build,
                            project=container_project_path,
                            package=container_package_dir,
                        )
                        execute_cmd(
                            docker=docker,
                            native_docker_image=options.manylinux_images[target_arch],
                            cmd_str=before_build_prepared,
                            before_build=True,
                            target_arch=target_arch,
                            env=env,
                        )

                    log.step("Building wheel...")

                    temp_dir = PurePath("/tmp/cibuildwheel")
                    built_wheel_dir = temp_dir / "built_wheel"
                    docker.call(["rm", "-rf", built_wheel_dir])
                    docker.call(["mkdir", "-p", built_wheel_dir])

                    verbosity_flags = get_build_verbosity_extra_flags(options.build_verbosity)

                    # pip wheel is not working properly with crossenv, use "bdist_wheel" for now
                    docker.call(
                        [
                            "python",
                            "setup.py",
                            "bdist_wheel",
                            f"--dist-dir={built_wheel_dir}",
                            *verbosity_flags,
                        ],
                        env=env,
                        cwd=container_package_dir,
                    )

                    built_wheel = docker.glob(built_wheel_dir, "*.whl")[0]

                    repaired_wheel_dir = temp_dir / "repaired_wheel"
                    assert env is not None
                    target_arch_env = TargetArchEnvUtil(env.get("CROSS_ROOT"), target_arch)
                    # Because we will repair the wheel in a different container, we need to
                    # changing the path with respect host machine. We will copy the built
                    # wheels on host machine before accessing these
                    built_wheel = PurePath(target_arch_env.host + built_wheel.__str__())
                    repaired_wheel_dir = PurePath(
                        target_arch_env.host + repaired_wheel_dir.__str__()
                    )

                    docker.call(["rm", "-rf", repaired_wheel_dir])
                    docker.call(["mkdir", "-p", repaired_wheel_dir])

                    if built_wheel.name.endswith("none-any.whl"):
                        raise NonPlatformWheelError()

                    # We will repair the wheel in a different environment, copy the
                    # built wheels back on host machine along with the script used to
                    # repair the wheel
                    docker.call(
                        ["cp", "-r", temp_dir, target_arch_env.host_machine_tmp_in_container]
                    )
                    docker.call(
                        [
                            "cp",
                            f"{target_arch_env.tmp}/repair_wheel.sh",
                            target_arch_env.host_machine_tmp_in_container,
                        ]
                    )
                    with DockerContainer(
                        options.manylinux_images[target_arch],
                        simulate_32_bit=platform_tag.endswith("i686"),
                        cwd=container_project_path,
                    ) as native_docker:
                        if options.repair_command:
                            log.step("Repairing wheel...")
                            repair_command_prepared = prepare_command(
                                options.repair_command,
                                wheel=built_wheel,
                                dest_dir=repaired_wheel_dir,
                            )
                            # Repair the wheel in a architecture specific container
                            native_docker.call(
                                [
                                    f"{target_arch_env.host_machine_tmp_in_container}/repair_wheel.sh",
                                    target_arch_env.host_machine_deps_in_container,
                                    repair_command_prepared,
                                ]
                            )
                        else:
                            native_docker.call(["mv", built_wheel, repaired_wheel_dir])
                        repaired_wheels = native_docker.glob(repaired_wheel_dir, "*.whl")

                        if options.test_command and options.test_selector(config.identifier):
                            log.step("Testing wheel...")

                            # We are testing in a different container so we need to copy the
                            # project and constraints file into it.
                            native_docker.copy_into(Path.cwd(), container_project_path)
                            native_docker.copy_into(constraints_file, container_constraints_file)

                            # Setting the path to current python version
                            envxc = native_docker.get_environment()
                            path = env["PATH"].replace("-xc", "")
                            envxc["PATH"] = f"{path}:envxc['PATH']"

                            # set up a virtual environment to install and test from, to make sure
                            # there are no dependencies that were pulled in at build time.
                            native_docker.call(
                                ["pip", "install", "virtualenv", *dependency_constraint_flags],
                                env=envxc,
                            )
                            venv_dir = (
                                PurePath(
                                    native_docker.call(
                                        ["mktemp", "-d"], capture_output=True
                                    ).strip()
                                )
                                / "venv"
                            )

                            native_docker.call(
                                ["python", "-m", "virtualenv", "--no-download", venv_dir], env=envxc
                            )

                            virtualenv_env = envxc.copy()
                            virtualenv_env["PATH"] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"

                            if options.before_test:
                                before_test_prepared = prepare_command(
                                    options.before_test,
                                    project=container_project_path,
                                    package=container_package_dir,
                                )
                                native_docker.call(
                                    ["sh", "-c", before_test_prepared], env=virtualenv_env
                                )

                            # Install the wheel we just built
                            # Note: If auditwheel produced two wheels, it's because the earlier produced wheel
                            # conforms to multiple manylinux standards. These multiple versions of the wheel are
                            # functionally the same, differing only in name, wheel metadata, and possibly include
                            # different external shared libraries. so it doesn't matter which one we run the tests on.
                            # Let's just pick the first one.
                            wheel_to_test = repaired_wheels[0]
                            native_docker.call(
                                ["pip", "install", str(wheel_to_test) + options.test_extras],
                                env=virtualenv_env,
                            )

                            # Install any requirements to run the tests
                            if options.test_requires:
                                native_docker.call(
                                    ["pip", "install", *options.test_requires], env=virtualenv_env
                                )

                            # Run the tests from a different directory
                            test_command_prepared = prepare_command(
                                options.test_command,
                                project=container_project_path,
                                package=container_package_dir,
                            )
                            native_docker.call(
                                ["sh", "-c", test_command_prepared], cwd="/root", env=virtualenv_env
                            )

                            # clean up test environment
                            native_docker.call(["rm", "-rf", venv_dir])

                    # move repaired wheels to output
                    docker.call(["mkdir", "-p", container_output_dir])
                    docker.call(["mv", *repaired_wheels, container_output_dir])

                    log.build_end()

                log.step("Copying wheels back to host...")
                # copy the output back into the host
                docker.copy_out(container_output_dir, options.output_dir)
                log.step_end()
        except subprocess.CalledProcessError as error:
            log.step_end_with_error(
                f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
            )
            troubleshoot(options.package_dir, error)
            sys.exit(1)


def troubleshoot(package_dir: Path, error: Exception) -> None:
    if isinstance(error, subprocess.CalledProcessError) and (
        error.cmd[0:4] == ["python", "-m", "pip", "wheel"]
        or error.cmd[0:3] == ["python", "-m", "build"]
    ):
        # the wheel build step failed
        print("Checking for common errors...")
        so_files = list(package_dir.glob("**/*.so"))

        if so_files:
            print(
                textwrap.dedent(
                    """
                    NOTE: Shared object (.so) files found in this project.

                    These files might be built against the wrong OS, causing problems with
                    auditwheel.

                    If you're using Cython and have previously done an in-place build,
                    remove those build files (*.so and *.c) before starting cibuildwheel.
                    """
                ),
                file=sys.stderr,
            )

            print("  Files detected:")
            print("\n".join(f"    {f}" for f in so_files))
            print("")
