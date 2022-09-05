from __future__ import annotations

import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath
from typing import Iterator, Tuple

from .architecture import Architecture
from .logger import log
from .oci_container import OCIContainer
from .options import Options
from .typing import OrderedDict, PathOrStr, assert_never
from .util import (
    AlreadyBuiltWheelError,
    BuildSelector,
    NonPlatformWheelError,
    find_compatible_wheel,
    get_build_verbosity_extra_flags,
    prepare_command,
    read_python_configs,
    split_config_settings,
    unwrap,
)


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    path_str: str

    @property
    def path(self) -> PurePosixPath:
        return PurePosixPath(self.path_str)


@dataclass(frozen=True)
class BuildStep:
    platform_configs: list[PythonConfiguration]
    platform_tag: str
    container_image: str


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: set[Architecture],
) -> list[PythonConfiguration]:

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


def container_image_for_python_configuration(config: PythonConfiguration, options: Options) -> str:
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
    options: Options, python_configurations: list[PythonConfiguration]
) -> Iterator[BuildStep]:
    """
    Groups PythonConfigurations into BuildSteps. Each BuildStep represents a
    separate container instance.
    """
    steps = OrderedDict[Tuple[str, str, str], BuildStep]()

    for config in python_configurations:
        _, platform_tag = config.identifier.split("-", 1)

        before_all = options.build_options(config.identifier).before_all
        container_image = container_image_for_python_configuration(config, options)

        step_key = (platform_tag, container_image, before_all)

        if step_key in steps:
            steps[step_key].platform_configs.append(config)
        else:
            steps[step_key] = BuildStep(
                platform_configs=[config],
                platform_tag=platform_tag,
                container_image=container_image,
            )

    yield from steps.values()


def build_in_container(
    *,
    options: Options,
    platform_configs: list[PythonConfiguration],
    container: OCIContainer,
    container_project_path: PurePath,
    container_package_dir: PurePath,
) -> None:
    container_output_dir = PurePosixPath("/output")

    log.step("Copying project into container...")
    container.copy_into(Path.cwd(), container_project_path)

    before_all_options_identifier = platform_configs[0].identifier
    before_all_options = options.build_options(before_all_options_identifier)

    if before_all_options.before_all:
        log.step("Running before_all...")

        env = container.get_environment()
        env["PATH"] = f'/opt/python/cp38-cp38/bin:{env["PATH"]}'
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env = before_all_options.environment.as_dictionary(
            env, executor=container.environment_executor
        )

        before_all_prepared = prepare_command(
            before_all_options.before_all,
            project=container_project_path,
            package=container_package_dir,
        )
        container.call(["sh", "-c", before_all_prepared], env=env)

    built_wheels: list[PurePosixPath] = []

    for config in platform_configs:
        log.build_start(config.identifier)
        build_options = options.build_options(config.identifier)

        dependency_constraint_flags: list[PathOrStr] = []

        if build_options.dependency_constraints:
            constraints_file = build_options.dependency_constraints.get_for_python_version(
                config.version
            )
            container_constraints_file = PurePath("/constraints.txt")

            container.copy_into(constraints_file, container_constraints_file)
            dependency_constraint_flags = ["-c", container_constraints_file]

        log.step("Setting up build environment...")

        env = container.get_environment()

        # put this config's python top of the list
        python_bin = config.path / "bin"
        env["PATH"] = f'{python_bin}:{env["PATH"]}'

        env = build_options.environment.as_dictionary(env, executor=container.environment_executor)

        # check config python is still on PATH
        which_python = container.call(["which", "python"], env=env, capture_output=True).strip()
        if PurePosixPath(which_python) != python_bin / "python":
            print(
                "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
                file=sys.stderr,
            )
            sys.exit(1)

        which_pip = container.call(["which", "pip"], env=env, capture_output=True).strip()
        if PurePosixPath(which_pip) != python_bin / "pip":
            print(
                "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
                file=sys.stderr,
            )
            sys.exit(1)

        compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
        if compatible_wheel:
            log.step_end()
            print(
                f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with {config.identifier}. Skipping build step..."
            )
            repaired_wheels = [compatible_wheel]
        else:

            if build_options.before_build:
                log.step("Running before_build...")
                before_build_prepared = prepare_command(
                    build_options.before_build,
                    project=container_project_path,
                    package=container_package_dir,
                )
                container.call(["sh", "-c", before_build_prepared], env=env)

            log.step("Building wheel...")

            temp_dir = PurePosixPath("/tmp/cibuildwheel")
            built_wheel_dir = temp_dir / "built_wheel"
            container.call(["rm", "-rf", built_wheel_dir])
            container.call(["mkdir", "-p", built_wheel_dir])

            verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
            extra_flags = split_config_settings(build_options.config_settings)

            if build_options.build_frontend == "pip":
                extra_flags += verbosity_flags
                container.call(
                    [
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        container_package_dir,
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *extra_flags,
                    ],
                    env=env,
                )
            elif build_options.build_frontend == "build":
                verbosity_setting = " ".join(verbosity_flags)
                extra_flags += (f"--config-setting={verbosity_setting}",)
                container.call(
                    [
                        "python",
                        "-m",
                        "build",
                        container_package_dir,
                        "--wheel",
                        f"--outdir={built_wheel_dir}",
                        *extra_flags,
                    ],
                    env=env,
                )
            else:
                assert_never(build_options.build_frontend)

            built_wheel = container.glob(built_wheel_dir, "*.whl")[0]

            repaired_wheel_dir = temp_dir / "repaired_wheel"
            container.call(["rm", "-rf", repaired_wheel_dir])
            container.call(["mkdir", "-p", repaired_wheel_dir])

            if built_wheel.name.endswith("none-any.whl"):
                raise NonPlatformWheelError()

            if build_options.repair_command:
                log.step("Repairing wheel...")
                repair_command_prepared = prepare_command(
                    build_options.repair_command, wheel=built_wheel, dest_dir=repaired_wheel_dir
                )
                container.call(["sh", "-c", repair_command_prepared], env=env)
            else:
                container.call(["mv", built_wheel, repaired_wheel_dir])

            repaired_wheels = container.glob(repaired_wheel_dir, "*.whl")

            for repaired_wheel in repaired_wheels:
                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise AlreadyBuiltWheelError(repaired_wheel.name)

        if build_options.test_command and build_options.test_selector(config.identifier):
            log.step("Testing wheel...")

            # set up a virtual environment to install and test from, to make sure
            # there are no dependencies that were pulled in at build time.
            container.call(["pip", "install", "virtualenv", *dependency_constraint_flags], env=env)
            venv_dir = (
                PurePath(container.call(["mktemp", "-d"], capture_output=True).strip()) / "venv"
            )

            container.call(["python", "-m", "virtualenv", "--no-download", venv_dir], env=env)

            virtualenv_env = env.copy()
            virtualenv_env["PATH"] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"

            if build_options.before_test:
                before_test_prepared = prepare_command(
                    build_options.before_test,
                    project=container_project_path,
                    package=container_package_dir,
                )
                container.call(["sh", "-c", before_test_prepared], env=virtualenv_env)

            # Install the wheel we just built
            # Note: If auditwheel produced two wheels, it's because the earlier produced wheel
            # conforms to multiple manylinux standards. These multiple versions of the wheel are
            # functionally the same, differing only in name, wheel metadata, and possibly include
            # different external shared libraries. so it doesn't matter which one we run the tests on.
            # Let's just pick the first one.
            wheel_to_test = repaired_wheels[0]
            container.call(
                ["pip", "install", str(wheel_to_test) + build_options.test_extras],
                env=virtualenv_env,
            )

            # Install any requirements to run the tests
            if build_options.test_requires:
                container.call(["pip", "install", *build_options.test_requires], env=virtualenv_env)

            # Run the tests from a different directory
            test_command_prepared = prepare_command(
                build_options.test_command,
                project=container_project_path,
                package=container_package_dir,
            )
            container.call(["sh", "-c", test_command_prepared], cwd="/root", env=virtualenv_env)

            # clean up test environment
            container.call(["rm", "-rf", venv_dir])

        # move repaired wheels to output
        if compatible_wheel is None:
            container.call(["mkdir", "-p", container_output_dir])
            container.call(["mv", *repaired_wheels, container_output_dir])
            built_wheels.extend(
                container_output_dir / repaired_wheel.name for repaired_wheel in repaired_wheels
            )

        log.build_end()

    log.step("Copying wheels back to host...")
    # copy the output back into the host
    container.copy_out(container_output_dir, options.globals.output_dir)
    log.step_end()


def build(options: Options, tmp_path: Path) -> None:  # pylint: disable=unused-argument
    try:
        # check the container engine is installed
        subprocess.run(
            [options.globals.container_engine, "--version"], check=True, stdout=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print(
            unwrap(
                f"""
                cibuildwheel: {options.globals.container_engine} not found. An
                OCI exe like Docker or Podman is required to run Linux builds.
                If you're building on Travis CI, add `services: [docker]` to
                your .travis.yml. If you're building on Circle CI in Linux,
                add a `setup_remote_docker` step to your .circleci/config.yml.
                If you're building on Cirrus CI, use `docker_builder` task.
                """
            ),
            file=sys.stderr,
        )
        sys.exit(2)

    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    cwd = Path.cwd()
    abs_package_dir = options.globals.package_dir.resolve()
    if cwd != abs_package_dir and cwd not in abs_package_dir.parents:
        msg = "package_dir must be inside the working directory"
        raise Exception(msg)

    container_project_path = PurePosixPath("/project")
    container_package_dir = container_project_path / abs_package_dir.relative_to(cwd)

    for build_step in get_build_steps(options, python_configurations):
        try:
            ids_to_build = [x.identifier for x in build_step.platform_configs]
            log.step(f"Starting container image {build_step.container_image}...")

            print(f"info: This container will host the build for {', '.join(ids_to_build)}...")

            with OCIContainer(
                image=build_step.container_image,
                simulate_32_bit=build_step.platform_tag.endswith("i686"),
                cwd=container_project_path,
                engine=options.globals.container_engine,
            ) as container:

                build_in_container(
                    options=options,
                    platform_configs=build_step.platform_configs,
                    container=container,
                    container_project_path=container_project_path,
                    container_package_dir=container_package_dir,
                )

        except subprocess.CalledProcessError as error:
            log.step_end_with_error(
                f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
            )
            troubleshoot(options, error)
            sys.exit(1)


def _matches_prepared_command(error_cmd: list[str], command_template: str) -> bool:
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
