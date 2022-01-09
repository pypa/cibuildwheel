import subprocess
import sys
import textwrap
from pathlib import Path, PurePath
from typing import Iterator, List, NamedTuple, Set, Tuple

from .architecture import Architecture
from .backend import BuilderBackend, test_one
from .docker_container import DockerContainer
from .logger import log
from .options import Options
from .typing import OrderedDict
from .util import BuildSelector, prepare_command, read_python_configs
from .virtualenv import FakeVirtualEnv


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


def build_one(
    config: PythonConfiguration,
    options: Options,
    docker: DockerContainer,
    container_output_dir: PurePath,
) -> None:
    log.build_start(config.identifier)
    build_options = options.build_options(config.identifier)

    log.step("Setting up build environment...")

    # put this config's python top of the list
    python_bin = config.path / "bin"
    base_python = python_bin / "python"
    venv = FakeVirtualEnv(docker, base_python, config.path)
    venv.env = build_options.environment.as_dictionary(
        venv.env, executor=docker.environment_executor
    )

    # check config python is still on PATH
    which_python = venv.call("which", "python", capture_stdout=True).strip()
    if PurePath(which_python) != base_python:
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    which_pip = venv.call("which", "pip", capture_stdout=True).strip()
    if PurePath(which_pip) != python_bin / "pip":
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    with docker.tmp_dir("repaired_wheel_dir") as repaired_wheel_dir:
        builder = BuilderBackend(build_options, venv, config.identifier)
        repaired_wheels = builder.build(repaired_wheel_dir)

        if build_options.test_command and build_options.test_selector(config.identifier):
            log.step("Testing wheel...")
            constraints = {"pip": "embed", "setuptools": "embed", "wheel": "embed"}
            # Note: If auditwheel<4.0.0 produced two wheels, it's because the earlier produced wheel
            # conforms to multiple manylinux standards. These multiple versions of the wheel are
            # functionally the same, differing only in name, wheel metadata, and possibly include
            # different external shared libraries. so it doesn't matter which one we run the tests on.
            # Let's just pick the first one.
            test_one(docker, base_python, constraints, build_options, repaired_wheels[0])

        # move repaired wheels to output
        docker.mkdir(container_output_dir, parents=True, exist_ok=True)
        docker.call("mv", *repaired_wheels, container_output_dir)

    log.build_end()


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
        docker.call("sh", "-c", before_all_prepared, env=env)

    for config in platform_configs:
        build_one(config, options, docker, container_output_dir)

    log.step("Copying wheels back to host...")
    # copy the output back into the host
    docker.copy_out(container_output_dir, options.globals.output_dir)
    log.step_end()


def build(options: Options, tmp_path: Path) -> None:
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
        list(error.cmd[0:4]) == ["python", "-m", "pip", "wheel"]
        or list(error.cmd[0:3]) == ["python", "-m", "build"]
        or _matches_prepared_command(
            list(error.cmd), options.build_options(None).repair_command
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
