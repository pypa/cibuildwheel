import subprocess
import sys
import textwrap
from pathlib import Path, PurePath
from typing import List, NamedTuple, Set

from .architecture import Architecture
from .docker_container import DockerContainer
from .logger import log
from .typing import PathOrStr, assert_never
from .util import (
    BuildOptions,
    BuildSelector,
    NonPlatformWheelError,
    get_build_verbosity_extra_flags,
    prepare_command,
    read_python_configs,
)


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

    full_python_configs = read_python_configs("linux")

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
        ("cp", "manylinux_x86_64", options.manylinux_images["x86_64"]),
        ("cp", "manylinux_i686", options.manylinux_images["i686"]),
        ("cp", "manylinux_aarch64", options.manylinux_images["aarch64"]),
        ("cp", "manylinux_ppc64le", options.manylinux_images["ppc64le"]),
        ("cp", "manylinux_s390x", options.manylinux_images["s390x"]),
        ("pp", "manylinux_x86_64", options.manylinux_images["pypy_x86_64"]),
        ("pp", "manylinux_aarch64", options.manylinux_images["pypy_aarch64"]),
        ("pp", "manylinux_i686", options.manylinux_images["pypy_i686"]),
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
                    docker.call(["sh", "-c", before_all_prepared], env=env)

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
                        docker.call(["sh", "-c", before_build_prepared], env=env)

                    log.step("Building wheel...")

                    temp_dir = PurePath("/tmp/cibuildwheel")
                    built_wheel_dir = temp_dir / "built_wheel"
                    docker.call(["rm", "-rf", built_wheel_dir])
                    docker.call(["mkdir", "-p", built_wheel_dir])

                    verbosity_flags = get_build_verbosity_extra_flags(options.build_verbosity)

                    if options.build_frontend == "pip":
                        docker.call(
                            [
                                "python",
                                "-m",
                                "pip",
                                "wheel",
                                container_package_dir,
                                f"--wheel-dir={built_wheel_dir}",
                                "--no-deps",
                                *verbosity_flags,
                            ],
                            env=env,
                        )
                    elif options.build_frontend == "build":
                        config_setting = " ".join(verbosity_flags)
                        docker.call(
                            [
                                "python",
                                "-m",
                                "build",
                                container_package_dir,
                                "--wheel",
                                f"--outdir={built_wheel_dir}",
                                f"--config-setting={config_setting}",
                            ],
                            env=env,
                        )
                    else:
                        assert_never(options.build_frontend)

                    built_wheel = docker.glob(built_wheel_dir, "*.whl")[0]

                    repaired_wheel_dir = temp_dir / "repaired_wheel"
                    docker.call(["rm", "-rf", repaired_wheel_dir])
                    docker.call(["mkdir", "-p", repaired_wheel_dir])

                    if built_wheel.name.endswith("none-any.whl"):
                        raise NonPlatformWheelError()

                    if options.repair_command:
                        log.step("Repairing wheel...")
                        repair_command_prepared = prepare_command(
                            options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir
                        )
                        docker.call(["sh", "-c", repair_command_prepared], env=env)
                    else:
                        docker.call(["mv", built_wheel, repaired_wheel_dir])

                    repaired_wheels = docker.glob(repaired_wheel_dir, "*.whl")

                    if options.test_command and options.test_selector(config.identifier):
                        log.step("Testing wheel...")

                        # set up a virtual environment to install and test from, to make sure
                        # there are no dependencies that were pulled in at build time.
                        docker.call(
                            ["pip", "install", "virtualenv", *dependency_constraint_flags], env=env
                        )
                        venv_dir = (
                            PurePath(docker.call(["mktemp", "-d"], capture_output=True).strip())
                            / "venv"
                        )

                        docker.call(
                            ["python", "-m", "virtualenv", "--no-download", venv_dir], env=env
                        )

                        virtualenv_env = env.copy()
                        virtualenv_env["PATH"] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"

                        if options.before_test:
                            before_test_prepared = prepare_command(
                                options.before_test,
                                project=container_project_path,
                                package=container_package_dir,
                            )
                            docker.call(["sh", "-c", before_test_prepared], env=virtualenv_env)

                        # Install the wheel we just built
                        # Note: If auditwheel produced two wheels, it's because the earlier produced wheel
                        # conforms to multiple manylinux standards. These multiple versions of the wheel are
                        # functionally the same, differing only in name, wheel metadata, and possibly include
                        # different external shared libraries. so it doesn't matter which one we run the tests on.
                        # Let's just pick the first one.
                        wheel_to_test = repaired_wheels[0]
                        docker.call(
                            ["pip", "install", str(wheel_to_test) + options.test_extras],
                            env=virtualenv_env,
                        )

                        # Install any requirements to run the tests
                        if options.test_requires:
                            docker.call(
                                ["pip", "install", *options.test_requires], env=virtualenv_env
                            )

                        # Run the tests from a different directory
                        test_command_prepared = prepare_command(
                            options.test_command,
                            project=container_project_path,
                            package=container_package_dir,
                        )
                        docker.call(
                            ["sh", "-c", test_command_prepared], cwd="/root", env=virtualenv_env
                        )

                        # clean up test environment
                        docker.call(["rm", "-rf", venv_dir])

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
