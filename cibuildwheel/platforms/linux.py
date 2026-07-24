from __future__ import annotations

__lazy_modules__ = {
    "cibuildwheel.audit",
    "cibuildwheel.frontend",
    "cibuildwheel.logger",
    "cibuildwheel.util",
    "cibuildwheel.util.file",
    "cibuildwheel.util.helpers",
    "collections",
    "contextlib",
    "functools",
    "pathlib",
    "shutil",
    "subprocess",
    "textwrap",
    "typing",
}

import contextlib
import dataclasses
import functools
import shutil
import subprocess
import sys
import textwrap
from collections import OrderedDict
from pathlib import Path, PurePath, PurePosixPath
from typing import ClassVar, assert_never

from cibuildwheel import errors
from cibuildwheel.architecture import Architecture
from cibuildwheel.audit import needs_audit, run_audit
from cibuildwheel.frontend import get_build_frontend_extra_flags, prepare_config_settings
from cibuildwheel.logger import log
from cibuildwheel.oci_container import OCIContainer, OCIContainerEngineConfig, OCIPlatform
from cibuildwheel.platforms import runner
from cibuildwheel.util import resources
from cibuildwheel.util.file import copy_test_sources
from cibuildwheel.util.helpers import prepare_command, unwrap

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence, Set

    from cibuildwheel.options import BuildOptions, Options
    from cibuildwheel.selector import BuildSelector
    from cibuildwheel.typing import PathOrStr

ARCHITECTURE_OCI_PLATFORM_MAP = {
    Architecture.x86_64: OCIPlatform.AMD64,
    Architecture.i686: OCIPlatform.i386,
    Architecture.aarch64: OCIPlatform.ARM64,
    Architecture.ppc64le: OCIPlatform.PPC64LE,
    Architecture.s390x: OCIPlatform.S390X,
    Architecture.armv7l: OCIPlatform.ARMV7,
    Architecture.riscv64: OCIPlatform.RISCV64,
}


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    identifier: str
    path_str: str

    @property
    def path(self) -> PurePosixPath:
        return PurePosixPath(self.path_str)


@dataclasses.dataclass(frozen=True, kw_only=True)
class BuildStep:
    platform_configs: list[PythonConfiguration]
    platform_tag: str
    container_engine: OCIContainerEngineConfig
    container_image: str


def all_python_configurations() -> list[PythonConfiguration]:
    config_dicts = resources.read_python_configs("linux")
    return [PythonConfiguration(**item) for item in config_dicts]


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> list[PythonConfiguration]:
    python_configurations = all_python_configurations()

    # return all configurations whose arch is in our `architectures` set,
    # and match the build/skip rules
    return [
        c
        for c in python_configurations
        if any(c.identifier.endswith(arch.value) for arch in architectures)
        and build_selector(c.identifier)
    ]


def container_image_for_python_configuration(
    config: PythonConfiguration, build_options: BuildOptions
) -> str:
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
    steps = OrderedDict[tuple[str, str, str, OCIContainerEngineConfig], BuildStep]()

    for config in python_configurations:
        _, platform_tag = config.identifier.split("-", 1)

        build_options = options.build_options(config.identifier)

        before_all = build_options.before_all
        container_image = container_image_for_python_configuration(config, build_options)
        container_engine = build_options.container_engine

        step_key = (platform_tag, container_image, before_all, container_engine)

        if step_key in steps:
            steps[step_key].platform_configs.append(config)
        else:
            steps[step_key] = BuildStep(
                platform_configs=[config],
                platform_tag=platform_tag,
                container_engine=container_engine,
                container_image=container_image,
            )

    yield from steps.values()


def check_all_python_exist(
    *, platform_configs: Iterable[PythonConfiguration], container: OCIContainer
) -> None:
    exist = True
    has_manylinux_interpreters = False
    messages = []

    with contextlib.suppress(subprocess.CalledProcessError):
        # use capture_output to keep quiet
        container.call(["manylinux-interpreters", "--help"], capture_output=True)
        has_manylinux_interpreters = True

    for config in platform_configs:
        python_path = config.path / "bin" / "python"
        if has_manylinux_interpreters:
            try:
                container.call(["manylinux-interpreters", "ensure", config.path.name])
            except subprocess.CalledProcessError:
                messages.append(
                    f"  'manylinux-interpreters ensure {config.path.name}' needed to build '{config.identifier}' failed in container running image '{container.image}'."
                    " Either the installation failed or this interpreter is not available in that image. Please check the logs."
                )
                exist = False
        else:
            try:
                container.call(["test", "-x", python_path])
            except subprocess.CalledProcessError:
                messages.append(
                    f"  '{python_path}' executable doesn't exist in image '{container.image}' to build '{config.identifier}'."
                )
                exist = False
    if not exist:
        message = "\n".join(messages)
        raise errors.FatalError(message)


@dataclasses.dataclass(frozen=True, kw_only=True)
class LinuxBuilder:
    """Steps to build one Linux wheel, invoked by runner.run_builds().

    Every step runs inside an OCI container, so wheel paths are container-side
    paths; the wheels are copied back to the host once, after every build in
    the container has finished.
    """

    identifier: str
    build_options: BuildOptions
    config: PythonConfiguration
    container: OCIContainer
    container_project_path: PurePath
    container_package_dir: PurePath
    # host-side scratch space, shared across identifiers
    local_tmp_dir: Path
    env: dict[str, str]
    python_bin: PurePosixPath
    use_uv: bool
    pip: list[str]
    dependency_constraint_flags: list[PathOrStr]
    container_output_dir: ClassVar[PurePosixPath] = PurePosixPath("/output")
    built_wheel_dir: ClassVar[PurePosixPath] = PurePosixPath("/tmp/cibuildwheel/built_wheel")
    repaired_wheel_dir: ClassVar[PurePosixPath] = PurePosixPath("/tmp/cibuildwheel/repaired_wheel")

    def before_build(self) -> None:
        build_options = self.build_options
        assert build_options.before_build is not None

        before_build_prepared = prepare_command(
            build_options.before_build,
            project=self.container_project_path,
            package=self.container_package_dir,
        )
        before_build_env = self.env.copy()
        if self.use_uv:
            # On Linux, no virtualenv is created for the build environment
            # (unlike macOS/Windows, where one is set up before before_build
            # runs). uv requires either an active venv or an explicit Python
            # target to install packages. Pin UV_PYTHON to the exact interpreter
            # for this build so that `uv pip install` works in before_build
            # without requiring users to pass --system.
            before_build_env["UV_PYTHON"] = str(self.python_bin / "python")
        self.container.call(["sh", "-c", before_build_prepared], env=before_build_env)

    def build_wheel(self) -> PurePosixPath:
        container = self.container
        build_options = self.build_options
        build_frontend = build_options.build_frontend

        container.call(["rm", "-rf", self.built_wheel_dir])
        container.call(["mkdir", "-p", self.built_wheel_dir])

        extra_flags = get_build_frontend_extra_flags(
            build_frontend,
            build_options.build_verbosity,
            prepare_config_settings(
                build_options.config_settings,
                project=self.container_project_path,
                package=self.container_package_dir,
            ),
        )

        match build_frontend.name:
            case "pip":
                container.call(
                    [
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        self.container_package_dir,
                        f"--wheel-dir={self.built_wheel_dir}",
                        "--no-deps",
                        *extra_flags,
                    ],
                    env=self.env,
                )
            case "build" | "build[uv]":
                if self.use_uv and "--no-isolation" not in extra_flags and "-n" not in extra_flags:
                    extra_flags += ["--installer=uv"]
                container.call(
                    [
                        "python",
                        "-m",
                        "build",
                        self.container_package_dir,
                        "--wheel",
                        f"--outdir={self.built_wheel_dir}",
                        *extra_flags,
                    ],
                    env=self.env,
                )
            case "uv":
                container.call(
                    [
                        "uv",
                        "build",
                        f"--python={self.python_bin / 'python'}",
                        self.container_package_dir,
                        "--wheel",
                        f"--out-dir={self.built_wheel_dir}",
                        *extra_flags,
                    ],
                    env=self.env,
                )
            case "pyodide-build":
                msg = "The 'pyodide-build' build frontend is not supported on this platform"
                raise errors.FatalError(msg)
            case _:
                assert_never(build_frontend)

        try:
            return container.glob(self.built_wheel_dir, "*.whl")[0]
        except IndexError:
            raise errors.BuildProducedNoWheelError() from None

    def repair_wheel(self, built_wheel: PurePosixPath) -> list[PurePosixPath]:
        container = self.container
        build_options = self.build_options

        container.call(["rm", "-rf", self.repaired_wheel_dir])
        container.call(["mkdir", "-p", self.repaired_wheel_dir])

        if build_options.repair_command:
            repair_command_prepared = prepare_command(
                build_options.repair_command,
                wheel=built_wheel,
                dest_dir=self.repaired_wheel_dir,
                package=self.container_package_dir,
                project=self.container_project_path,
            )
            container.call(["sh", "-c", repair_command_prepared], env=self.env)
        else:
            container.call(["mv", built_wheel, self.repaired_wheel_dir])

        return container.glob(self.repaired_wheel_dir, "*.whl")

    def audit_wheel(self, repaired_wheel: PurePosixPath) -> None:
        build_options = self.build_options
        if not needs_audit(build_options.audit_command, repaired_wheel.name):
            return

        # the wheel lives in the container, but the audit tools run on the
        # host; copy it out to a temporary directory first
        local_abi3audit_dir = self.local_tmp_dir / self.identifier / "audit"
        local_abi3audit_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.container.copy_out(self.repaired_wheel_dir, local_abi3audit_dir)
            local_wheel = local_abi3audit_dir / repaired_wheel.name
            run_audit(tmp_dir=self.local_tmp_dir, build_options=build_options, wheel=local_wheel)
        finally:
            shutil.rmtree(local_abi3audit_dir, ignore_errors=True)

    def test_wheel(self, repaired_wheel: PurePosixPath) -> None:
        container = self.container
        build_options = self.build_options
        assert build_options.test_command is not None

        log.step("Testing wheel...")

        # set up a virtual environment to install and test from, to make sure
        # there are no dependencies that were pulled in at build time.
        if not self.use_uv:
            container.call(
                ["pip", "install", "virtualenv", *self.dependency_constraint_flags], env=self.env
            )

        testing_temp_dir = PurePosixPath(
            container.call(["mktemp", "-d"], capture_output=True).strip()
        )
        venv_dir = testing_temp_dir / "venv"

        if self.use_uv:
            container.call(
                ["uv", "venv", venv_dir, "--python", self.python_bin / "python"], env=self.env
            )
        else:
            # Use embedded dependencies from virtualenv to ensure determinism
            venv_args = ["--no-periodic-update", "--pip=embed", "--no-setuptools"]
            if "38" in self.identifier:
                venv_args.append("--no-wheel")
            container.call(["python", "-m", "virtualenv", *venv_args, venv_dir], env=self.env)

        virtualenv_env = self.env.copy()
        virtualenv_env["PATH"] = f"{venv_dir / 'bin'}:{virtualenv_env['PATH']}"
        virtualenv_env["VIRTUAL_ENV"] = str(venv_dir)
        virtualenv_env = build_options.test_environment.as_dictionary(
            prev_environment=virtualenv_env
        )

        if build_options.before_test:
            before_test_prepared = prepare_command(
                build_options.before_test,
                project=self.container_project_path,
                package=self.container_package_dir,
            )
            container.call(["sh", "-c", before_test_prepared], env=virtualenv_env)

        # Install the wheel we just built
        container.call(
            [*self.pip, "install", str(repaired_wheel) + build_options.test_extras],
            env=virtualenv_env,
        )

        # Install any requirements to run the tests
        if build_options.test_requires:
            container.call([*self.pip, "install", *build_options.test_requires], env=virtualenv_env)

        # Run the tests from a different directory
        test_command_prepared = prepare_command(
            build_options.test_command,
            project=self.container_project_path,
            package=self.container_package_dir,
            wheel=repaired_wheel,
        )

        test_cwd = testing_temp_dir / "test_cwd"
        container.call(["mkdir", "-p", test_cwd])

        if build_options.test_sources:
            copy_test_sources(
                build_options.test_sources,
                Path.cwd(),
                test_cwd,
                copy_into=container.copy_into,
            )
        else:
            # Use the test_fail.py file to raise a nice error if the user
            # tries to run tests in the cwd
            container.copy_into(resources.TEST_FAIL_CWD_FILE, test_cwd / "test_fail.py")

        container.call(["sh", "-c", test_command_prepared], cwd=test_cwd, env=virtualenv_env)

        # clean up test environment
        container.call(["rm", "-rf", testing_temp_dir])

    def move_to_output(self, repaired_wheel: PurePosixPath) -> PurePosixPath:
        self.container.call(["mkdir", "-p", self.container_output_dir])
        self.container.call(["mv", repaired_wheel, self.container_output_dir])
        return self.container_output_dir / repaired_wheel.name

    def cleanup(self) -> None:
        # nothing to do: the container is removed when the build step ends,
        # and the host temp dir is removed at the end of the run
        pass


def setup_builder(
    config: PythonConfiguration,
    build_options: BuildOptions,
    container: OCIContainer,
    container_project_path: PurePath,
    container_package_dir: PurePath,
    local_tmp_dir: Path,
) -> LinuxBuilder:
    """Prepare the container's build environment for one identifier."""
    use_uv = build_options.build_frontend.name in {"build[uv]", "uv"}

    log.step("Setting up build environment...")

    dependency_constraint_flags: list[PathOrStr] = []
    local_identifier_tmp_dir = local_tmp_dir / config.identifier
    local_identifier_tmp_dir.mkdir(parents=True, exist_ok=True)
    local_constraints_file = build_options.dependency_constraints.get_for_python_version(
        version=config.version,
        tmp_dir=local_identifier_tmp_dir,
    )
    if local_constraints_file:
        container_constraints_file = PurePosixPath("/constraints.txt")
        container.copy_into(local_constraints_file, container_constraints_file)
        dependency_constraint_flags = ["-c", container_constraints_file]

    env = container.get_environment()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_ROOT_USER_ACTION"] = "ignore"

    # put this config's python top of the list
    python_bin = config.path / "bin"
    env["PATH"] = f"{python_bin}:{env['PATH']}"

    env = build_options.environment.as_dictionary(env, executor=container.environment_executor)
    env["CIBUILDWHEEL_BUILD_IDENTIFIER"] = config.identifier

    # check config python is still on PATH
    which_python = container.call(["which", "python"], env=env, capture_output=True).strip()
    if PurePosixPath(which_python) != python_bin / "python":
        msg = "python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it."
        raise errors.FatalError(msg)
    container.call(["python", "-V", "-V"], env=env)

    if use_uv:
        which_uv = container.call(["which", "uv"], env=env, capture_output=True).strip()
        if not which_uv:
            msg = "uv not found on PATH. You must use a supported manylinux or musllinux environment with uv."
            raise errors.FatalError(msg)
    else:
        which_pip = container.call(["which", "pip"], env=env, capture_output=True).strip()
        if PurePosixPath(which_pip) != python_bin / "pip":
            msg = "pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it."
            raise errors.FatalError(msg)

    return LinuxBuilder(
        identifier=config.identifier,
        build_options=build_options,
        config=config,
        container=container,
        container_project_path=container_project_path,
        container_package_dir=container_package_dir,
        local_tmp_dir=local_tmp_dir,
        env=env,
        python_bin=python_bin,
        use_uv=use_uv,
        pip=["uv", "pip"] if use_uv else ["pip"],
        dependency_constraint_flags=dependency_constraint_flags,
    )


def build_in_container(
    *,
    options: Options,
    platform_configs: Sequence[PythonConfiguration],
    container: OCIContainer,
    container_project_path: PurePath,
    container_package_dir: PurePath,
    local_tmp_dir: Path,
) -> None:
    check_all_python_exist(platform_configs=platform_configs, container=container)

    log.step("Copying project into container...")
    container.copy_into(Path.cwd(), container_project_path)

    # before_all runs once per container, not once per session
    before_all_options_identifier = platform_configs[0].identifier
    before_all_options = options.build_options(before_all_options_identifier)

    if before_all_options.before_all:
        log.step("Running before_all...")

        env = container.get_environment()
        env["PATH"] = f"/opt/python/cp39-cp39/bin:{env['PATH']}"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["PIP_ROOT_USER_ACTION"] = "ignore"
        env = before_all_options.environment.as_dictionary(
            env, executor=container.environment_executor
        )

        before_all_prepared = prepare_command(
            before_all_options.before_all,
            project=container_project_path,
            package=container_package_dir,
        )
        container.call(["sh", "-c", before_all_prepared], env=env)

    runner.run_builds(
        [
            runner.BuildSpec(
                identifier=config.identifier,
                setup=functools.partial(
                    setup_builder,
                    config=config,
                    build_options=options.build_options(config.identifier),
                    container=container,
                    container_project_path=container_project_path,
                    container_package_dir=container_package_dir,
                    local_tmp_dir=local_tmp_dir,
                ),
            )
            for config in platform_configs
        ]
    )

    log.step("Copying wheels back to host...")
    # copy the output back into the host
    container.copy_out(PurePosixPath("/output"), options.globals.output_dir)
    log.step_end()


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    cwd = Path.cwd()
    abs_package_dir = options.globals.package_dir.resolve()
    if cwd != abs_package_dir and cwd not in abs_package_dir.parents:
        msg = "package_dir must be inside the working directory"
        raise errors.ConfigurationError(msg)

    container_project_path = PurePosixPath("/project")
    container_package_dir = container_project_path / abs_package_dir.relative_to(cwd)

    for build_step in get_build_steps(options, python_configurations):
        try:
            # check the container engine is installed
            subprocess.run(
                [build_step.container_engine.name, "--version"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as error:
            msg = unwrap(
                f"""
                {build_step.container_engine.name} not found. An OCI exe like
                Docker or Podman is required to run Linux builds. If you're
                building on Travis CI, add `services: [docker]` to your
                .travis.yml. If you're building on Circle CI in Linux, add a
                `setup_remote_docker` step to your .circleci/config.yml.
                """
            )
            raise errors.ConfigurationError(msg) from error

        with runner.fatal_on_called_process_error(functools.partial(troubleshoot, options)):
            ids_to_build = [x.identifier for x in build_step.platform_configs]
            log.step(f"Starting container image {build_step.container_image}...")

            print(f"info: This container will host the build for {', '.join(ids_to_build)}...")
            architecture = Architecture(build_step.platform_tag.split("_", 1)[1])

            with OCIContainer(
                image=build_step.container_image,
                oci_platform=ARCHITECTURE_OCI_PLATFORM_MAP[architecture],
                cwd=container_project_path,
                engine=build_step.container_engine,
            ) as container:
                build_in_container(
                    options=options,
                    platform_configs=build_step.platform_configs,
                    container=container,
                    container_project_path=container_project_path,
                    container_package_dir=container_package_dir,
                    local_tmp_dir=tmp_path,
                )


def _matches_prepared_command(error_cmd: Sequence[str], command_template: str) -> bool:
    if len(error_cmd) < 3 or error_cmd[0:2] != ["sh", "-c"]:
        return False
    command_prefix = command_template.split("{", maxsplit=1)[0].strip()
    return error_cmd[2].startswith(command_prefix)


def troubleshoot(options: Options, error: Exception) -> None:
    if isinstance(error, subprocess.CalledProcessError) and (
        error.cmd[0:4] == ["python", "-m", "pip", "wheel"]
        or error.cmd[0:2] == ["uv", "build"]
        or error.cmd[0:3] == ["python", "-m", "build"]
        or _matches_prepared_command(
            error.cmd, options.build_options(None).repair_command
        )  # TODO allow matching of overrides too?
    ):
        # the wheel build step or the repair step failed
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
            print()
