import subprocess
import sys
import textwrap
from pathlib import Path, PurePath
from typing import Iterator, List, NamedTuple, Set, Tuple

from .architecture import Architecture
from .docker_container import DockerContainer
from .logger import log
from .options import Options
from .typing import OrderedDict, PathOrStr, assert_never
from .util import (
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


class BuildStep(NamedTuple):
    platform_configs: List[PythonConfiguration]
    platform_tag: str
    docker_image: str


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


def docker_image_for_python_configuration(config: PythonConfiguration, options: Options) -> str:
    build_options = options.build_options(config.identifier)
    # e.g
    # identifier is 'cp310-manylinux_x86_64'
    # platform_tag is 'manylinux_x86_64'
    # platform_arch is 'x86_64'
    _, platform_tag = config.identifier.split("-", 1)
    _, platform_arch = platform_tag.split("_", 1)

    assert build_options.manylinux_images is not None
    assert build_options.musllinux_images is not None

    return (
        build_options.manylinux_images[platform_arch]
        if platform_tag.startswith("manylinux")
        else build_options.musllinux_images[platform_arch]
    )


def get_build_steps(
    options: Options, python_configurations: List[PythonConfiguration]
) -> Iterator[BuildStep]:
    """
    Groups PythonConfigurations into BuildSteps. Each BuildStep represents a
    separate Docker container.
    """
    steps = OrderedDict[Tuple[str, str, str], BuildStep]()

    for config in python_configurations:
        _, platform_tag = config.identifier.split("-", 1)

        before_all = options.build_options(config.identifier).before_all
        docker_image = docker_image_for_python_configuration(config, options)

        step_key = (platform_tag, docker_image, before_all)

        if step_key in steps:
            steps[step_key].platform_configs.append(config)
        else:
            steps[step_key] = BuildStep(
                platform_configs=[config], platform_tag=platform_tag, docker_image=docker_image
            )

    yield from steps.values()


def build_on_docker(
    *,
    options: Options,
    platform_configs: List[PythonConfiguration],
    docker: DockerContainer,
    container_project_path: PurePath,
    container_package_dir: PurePath,
) -> None:
    container_output_dir = PurePath("/output")

    log.step("Copying project into Docker...")
    docker.copy_into(Path.cwd(), container_project_path)

    before_all_options_identifier = platform_configs[0].identifier
    before_all_options = options.build_options(before_all_options_identifier)

    if before_all_options.before_all:
        log.step("Running before_all...")

        env = docker.get_environment()
        env["PATH"] = f'/opt/python/cp38-cp38/bin:{env["PATH"]}'
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env = before_all_options.environment.as_dictionary(
            env, executor=docker.environment_executor
        )

        before_all_prepared = prepare_command(
            before_all_options.before_all,
            project=container_project_path,
            package=container_package_dir,
        )
        docker.call(["sh", "-c", before_all_prepared], env=env)

    for config in platform_configs:
        log.build_start(config.identifier)
        build_options = options.build_options(config.identifier)

        dependency_constraint_flags: List[PathOrStr] = []

        if build_options.dependency_constraints:
            constraints_file = build_options.dependency_constraints.get_for_python_version(
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

        env = build_options.environment.as_dictionary(env, executor=docker.environment_executor)

        # check config python is still on PATH
        which_python = docker.call(["which", "python"], env=env, capture_output=True).strip()
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

        if build_options.before_build:
            log.step("Running before_build...")
            before_build_prepared = prepare_command(
                build_options.before_build,
                project=container_project_path,
                package=container_package_dir,
            )
            docker.call(["sh", "-c", before_build_prepared], env=env)

        log.step("Building wheel...")

        temp_dir = PurePath("/tmp/cibuildwheel")
        built_wheel_dir = temp_dir / "built_wheel"
        docker.call(["rm", "-rf", built_wheel_dir])
        docker.call(["mkdir", "-p", built_wheel_dir])

        verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)

        if build_options.build_frontend == "pip":
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
        elif build_options.build_frontend == "build":
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
            assert_never(build_options.build_frontend)

        built_wheel = docker.glob(built_wheel_dir, "*.whl")[0]

        repaired_wheel_dir = temp_dir / "repaired_wheel"
        docker.call(["rm", "-rf", repaired_wheel_dir])
        docker.call(["mkdir", "-p", repaired_wheel_dir])

        if built_wheel.name.endswith("none-any.whl"):
            raise NonPlatformWheelError()

        if build_options.repair_command:
            log.step("Repairing wheel...")
            repair_command_prepared = prepare_command(
                build_options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir
            )
            docker.call(["sh", "-c", repair_command_prepared], env=env)
        else:
            docker.call(["mv", built_wheel, repaired_wheel_dir])

        repaired_wheels = docker.glob(repaired_wheel_dir, "*.whl")

        if build_options.test_command and build_options.test_selector(config.identifier):
            log.step("Testing wheel...")

            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            docker.call(["pip", "install", "virtualenv", *dependency_constraint_flags], env=env)
            venv_dir = PurePath(docker.call(["mktemp", "-d"], capture_output=True).strip()) / "venv"

            docker.call(["python", "-m", "virtualenv", "--no-download", venv_dir], env=env)

            virtualenv_env = env.copy()
            virtualenv_env["PATH"] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"

            if build_options.before_test:
                before_test_prepared = prepare_command(
                    build_options.before_test,
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
                ["pip", "install", str(wheel_to_test) + build_options.test_extras],
                env=virtualenv_env,
            )

            # Install any requirements to run the tests
            if build_options.test_requires:
                docker.call(["pip", "install", *build_options.test_requires], env=virtualenv_env)

            # Run the tests from a different directory
            test_command_prepared = prepare_command(
                build_options.test_command,
                project=container_project_path,
                package=container_package_dir,
            )
            docker.call(["sh", "-c", test_command_prepared], cwd="/root", env=virtualenv_env)

            # clean up test environment
            docker.call(["rm", "-rf", venv_dir])

        # move repaired wheels to output
        docker.call(["mkdir", "-p", container_output_dir])
        docker.call(["mv", *repaired_wheels, container_output_dir])

        log.build_end()

    log.step("Copying wheels back to host...")
    # copy the output back into the host
    docker.copy_out(container_output_dir, options.globals.output_dir)
    log.step_end()


def build(options: Options, tmp_path: Path) -> None:  # pylint: disable=unused-argument
    try:
        # check docker is installed
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(
            "cibuildwheel: Docker not found. Docker is required to run Linux builds. "
            "If you're building on Travis CI, add `services: [docker]` to your .travis.yml."
            "If you're building on Circle CI in Linux, add a `setup_remote_docker` step to your .circleci/config.yml",
            file=sys.stderr,
        )
        sys.exit(2)

    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    cwd = Path.cwd()
    abs_package_dir = options.globals.package_dir.resolve()
    if cwd != abs_package_dir and cwd not in abs_package_dir.parents:
        raise Exception("package_dir must be inside the working directory")

    container_project_path = PurePath("/project")
    container_package_dir = container_project_path / abs_package_dir.relative_to(cwd)

    for build_step in get_build_steps(options, python_configurations):
        try:
            ids_to_build = [x.identifier for x in build_step.platform_configs]
            log.step(
                f"Starting Docker image {build_step.docker_image} for {', '.join(ids_to_build)}..."
            )

            with DockerContainer(
                docker_image=build_step.docker_image,
                simulate_32_bit=build_step.platform_tag.endswith("i686"),
                cwd=container_project_path,
            ) as docker:

                build_on_docker(
                    options=options,
                    platform_configs=build_step.platform_configs,
                    docker=docker,
                    container_project_path=container_project_path,
                    container_package_dir=container_package_dir,
                )

        except subprocess.CalledProcessError as error:
            log.step_end_with_error(
                f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
            )
            troubleshoot(options, error)
            sys.exit(1)


def _matches_prepared_command(error_cmd: List[str], command_template: str) -> bool:
    if len(error_cmd) < 3 or error_cmd[0:2] != ["sh", "-c"]:
        return False
    command_prefix = command_template.split("{", maxsplit=1)[0].strip()
    return error_cmd[2].startswith(command_prefix)


def troubleshoot(options: Options, error: Exception) -> None:

    if isinstance(error, subprocess.CalledProcessError) and (
        error.cmd[0:4] == ["python", "-m", "pip", "wheel"]
        or error.cmd[0:3] == ["python", "-m", "build"]
        or _matches_prepared_command(
            error.cmd, options.build_options(None).repair_command
        )  # TODO allow matching of overrides too?
    ):
        # the wheel build step or the repair step failed
        print("Checking for common errors...")
        so_files = list(options.globals.package_dir.glob("**/*.so"))

        if so_files:
            print(
                textwrap.dedent(
                    """
                    NOTE: Shared object (.so) files found in this project.

                    These files might be built against the wrong OS, causing problems with
                    auditwheel. If possible, run cibuildwheel in a clean checkout.

                    If you're using Cython and have previously done an in-place build,
                    remove those build files (*.so and *.c) before starting cibuildwheel.

                    setuptools uses the build/ folder to store its build cache. It
                    may be necessary to remove those build files (*.so and *.o) before
                    starting cibuildwheel.

                    Files that belong to a virtual environment are probably not an issue
                    unless you used a custom command telling cibuildwheel to activate it.
                    """
                ),
                file=sys.stderr,
            )

            print("  Files detected:")
            print("\n".join(f"    {f}" for f in so_files))
            print("")
