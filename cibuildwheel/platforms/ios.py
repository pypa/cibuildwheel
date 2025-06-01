from __future__ import annotations

import dataclasses
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Sequence, Set
from pathlib import Path
from typing import assert_never

from filelock import FileLock

from .. import errors
from ..architecture import Architecture
from ..environment import ParsedEnvironment
from ..frontend import (
    BuildFrontendConfig,
    BuildFrontendName,
    get_build_frontend_extra_flags,
)
from ..logger import log
from ..options import Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell, split_command
from ..util.file import (
    CIBW_CACHE_PATH,
    copy_test_sources,
    download,
    move_file,
)
from ..util.helpers import prepare_command, unwrap_preserving_paragraphs
from ..util.packaging import (
    combine_constraints,
    find_compatible_wheel,
    get_pip_version,
)
from ..venv import constraint_flags, virtualenv
from .macos import install_cpython as install_build_cpython


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str
    build_url: str

    @property
    def sdk(self) -> str:
        return self.multiarch.rsplit("-", 1)[1]

    @property
    def arch(self) -> str:
        return self.multiarch.rsplit("-", 1)[0]

    @property
    def multiarch(self) -> str:
        # The multiarch identifier, as reported by `sys.implementation._multiarch`
        return "-".join(self.identifier.split("-ios_")[1].rsplit("_", 1))

    @property
    def is_simulator(self) -> bool:
        return self.identifier.endswith("_iphonesimulator")

    @property
    def xcframework_slice(self) -> str:
        "XCframeworks include binaries for multiple ABIs; which ABI section should be used?"
        return "ios-arm64_x86_64-simulator" if self.is_simulator else "ios-arm64"


def all_python_configurations() -> list[PythonConfiguration]:
    # iOS builds are always cross builds; we need to install a macOS Python as
    # well. Rather than duplicate the location of the URL of macOS installers,
    # load the macos configurations, determine the macOS configuration that
    # matches the platform we're building, and embed that URL in the parsed iOS
    # configuration.
    macos_python_configs = resources.read_python_configs("macos")

    def build_url(config_dict: dict[str, str]) -> str:
        # The iOS identifier will be something like cp313-ios_arm64_iphoneos.
        # Drop the iphoneos suffix, then replace ios with macosx to yield
        # cp313-macosx_arm64, which will be a macOS build identifier.
        modified_ios_identifier = config_dict["identifier"].rsplit("_", 1)[0]
        macos_identifier = modified_ios_identifier.replace("ios", "macosx")
        matching = [
            config for config in macos_python_configs if config["identifier"] == macos_identifier
        ]
        return matching[0]["url"]

    # Load the platform configuration
    full_python_configs = resources.read_python_configs("ios")
    # Build the configurations, annotating with macOS URL details.
    return [
        PythonConfiguration(
            **item,
            build_url=build_url(item),
        )
        for item in full_python_configs
    ]


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> list[PythonConfiguration]:
    python_configurations = all_python_configurations()

    # Filter out configs that don't match any of the selected architectures
    python_configurations = [
        c
        for c in python_configurations
        if any(c.identifier.endswith(f"-ios_{a.value}") for a in architectures)
    ]

    # Skip builds as required by BUILD/SKIP
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]

    return python_configurations


def install_target_cpython(tmp: Path, config: PythonConfiguration, free_threading: bool) -> Path:
    if free_threading:
        msg = "Free threading builds aren't available for iOS (yet)"
        raise errors.FatalError(msg)

    # Install an iOS build of CPython
    ios_python_tar_gz = config.url.rsplit("/", 1)[-1]
    extension = ".tar.gz"
    assert ios_python_tar_gz.endswith(extension)
    installation_path = CIBW_CACHE_PATH / ios_python_tar_gz[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            downloaded_tar_gz = tmp / ios_python_tar_gz
            download(config.url, downloaded_tar_gz)
            installation_path.mkdir(parents=True, exist_ok=True)
            call("tar", "-C", installation_path, "-xf", downloaded_tar_gz)
            downloaded_tar_gz.unlink()

    return installation_path


def cross_virtualenv(
    *,
    py_version: str,
    target_python: Path,
    multiarch: str,
    build_python: Path,
    venv_path: Path,
    dependency_constraint: Path | None,
    xbuild_tools: Sequence[str] | None,
) -> dict[str, str]:
    """Create a cross-compilation virtual environment.

    In a cross-compilation environment, the *target* is the platform where the
    code will ultimately run, and the *build* is the platform where you're
    running the compilation. When building iOS wheels, iOS is the target machine
    and macOS is the build machine. The terminology around these machines varies
    between build tools (configure uses "host" and "build"; cmake uses "target" and
    "build host").

    A cross-compilation virtualenv is an environment that is based on the
    *build* python (so that binaries can execute); but it modifies the
    environment at startup so that any request for platform details (such as
    `sys.platform` or `sysconfig.get_platform()`) return details of the target
    platform. It also applies a loader patch so that any virtualenv created by
    the cross-compilation environment will also be a cross-compilation
    environment.

    :param py_version: The Python version (major.minor) in use
    :param target_python: The path to the python binary for the target platform
    :param multiarch: The multiarch tag for the target platform (i.e., the value
        of `sys.implementation._multiarch`)
    :param build_python: The path to the python binary for the build platform
    :param venv_path: The path where the cross virtual environment should be
        created.
    :param dependency_constraint: A path to a constraint file that should be
        used when constraining dependencies in the environment.
    :param xbuild_tools: A list of executable names (without paths) that are
        on the path, but must be preserved in the cross environment.
    """
    # Create an initial macOS virtual environment
    env = virtualenv(
        py_version,
        build_python,
        venv_path,
        dependency_constraint,
        use_uv=False,
    )

    # Convert the macOS virtual environment into an iOS virtual environment
    # using the cross-platform conversion script in the iOS distribution.

    # target_python is the path to the Python binary;
    # determine the root of the XCframework slice that is being used.
    slice_path = target_python.parent.parent
    call(
        "python",
        str(slice_path / f"platform-config/{multiarch}/make_cross_venv.py"),
        str(venv_path),
        env=env,
        cwd=venv_path,
    )

    # When running on macOS, it's easy for the build environment to leak into
    # the target environment, especially when building for ARM64 (because the
    # build architecture is the same as the target architecture). The primary
    # culprit for this is Homebrew libraries leaking in as dependencies for iOS
    # libraries.
    #
    # To prevent problems, set the PATH to isolate the build environment from
    # sources that could introduce incompatible binaries.
    #
    # However, there may be some tools on the path that are needed for the
    # build. Find their location on the path, and link the underlying binaries
    # (fully resolving symlinks) to a "safe" location that will *only* contain
    # those tools. This avoids needing to add *all* of Homebrew to the path just
    # to get access to (for example) cmake for build purposes. A value of None
    # means the user hasn't provided a list of xbuild tools.
    xbuild_tools_path = venv_path / "cibw_xbuild_tools"
    xbuild_tools_path.mkdir()
    if xbuild_tools is None:
        log.warning(
            textwrap.dedent(
                """
                Your project configuration does not define any cross-build tools.

                iOS builds use an isolated build environment; if your build process requires any
                third-party tools (such as cmake, ninja, or rustc), you must explicitly declare
                that those tools are required using xbuild-tools/CIBW_XBUILD_TOOLS. This will
                likely manifest as a "somebuildtool: command not found" error.

                If the build succeeds, you can silence this warning by setting adding
                `xbuild-tools = []` to your pyproject.toml configuration, or exporting
                CIBW_XBUILD_TOOLS as an empty string into your environment.
                """
            )
        )
    else:
        for tool in xbuild_tools:
            tool_path = shutil.which(tool)
            if tool_path is None:
                msg = f"Could not find a {tool!r} executable on the path."
                raise errors.FatalError(msg)

            # Link the binary into the safe tools directory
            original = Path(tool_path).resolve()
            print(f"{tool!r} will be included in the cross-build environment (using {original})")
            (xbuild_tools_path / tool).symlink_to(original)

    env["PATH"] = os.pathsep.join(
        [
            # The target python's binary directory
            str(target_python.parent),
            # The cross-platform environment's binary directory
            str(venv_path / "bin"),
            # The directory of cross-build tools
            str(xbuild_tools_path),
            # The bare minimum Apple system paths.
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
            "/Library/Apple/usr/bin",
        ]
    )
    # Also unset DYLD_LIBRARY_PATH to ensure that no macOS libraries will be
    # found and linked.
    env.pop("DYLD_LIBRARY_PATH", None)

    return env


def setup_python(
    tmp: Path,
    *,
    python_configuration: PythonConfiguration,
    dependency_constraint: Path | None,
    environment: ParsedEnvironment,
    build_frontend: BuildFrontendName,
    xbuild_tools: Sequence[str] | None,
) -> tuple[Path, dict[str, str]]:
    if build_frontend == "build[uv]":
        msg = "uv doesn't support iOS"
        raise errors.FatalError(msg)

    # An iOS environment requires 2 python installs - one for the build machine
    # (macOS), and one for the target (iOS). We'll only ever interact with the
    # *target* python, but the build Python needs to exist to act as the base
    # for a cross venv.
    tmp.mkdir()
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Build Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        free_threading = "t-ios" in python_configuration.identifier
        build_python = install_build_cpython(
            tmp,
            python_configuration.version,
            python_configuration.build_url,
            free_threading,
        )
    else:
        msg = f"Unknown Python implementation: {implementation_id}"
        raise errors.FatalError(msg)

    assert build_python.exists(), (
        f"{build_python.name} not found, has {list(build_python.parent.iterdir())}"
    )

    log.step(f"Installing Target Python {implementation_id}...")
    target_install_path = install_target_cpython(tmp, python_configuration, free_threading)
    target_python = (
        target_install_path
        / "Python.xcframework"
        / python_configuration.xcframework_slice
        / "bin"
        / f"python{python_configuration.version}"
    )

    assert target_python.exists(), (
        f"{target_python.name} not found, has {list(target_install_path.iterdir())}"
    )

    log.step("Creating cross build environment...")

    venv_path = tmp / "venv"
    env = cross_virtualenv(
        py_version=python_configuration.version,
        target_python=target_python,
        multiarch=python_configuration.multiarch,
        build_python=build_python,
        venv_path=venv_path,
        dependency_constraint=dependency_constraint,
        xbuild_tools=xbuild_tools,
    )
    venv_bin_path = venv_path / "bin"
    assert venv_bin_path.exists()

    # We version pip ourselves, so we don't care about pip version checking
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip'
    pip = ["python", "-m", "pip"]
    call(
        *pip,
        "install",
        "--upgrade",
        "pip",
        *constraint_flags(dependency_constraint),
        env=env,
        cwd=venv_path,
    )

    # Apply our environment after pip is ready
    env = environment.as_dictionary(prev_environment=env)

    # Check what Python version we're on
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    print(which_python)
    if which_python != str(venv_bin_path / "python"):
        msg = (
            "cibuildwheel: python available on PATH doesn't match our installed instance. "
            "If you have modified PATH, ensure that you don't overwrite cibuildwheel's "
            "entry or insert python above it."
        )
        raise errors.FatalError(msg)
    call("python", "--version", env=env)

    # Check what pip version we're on
    assert (venv_bin_path / "pip").exists()
    which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
    print(which_pip)
    if which_pip != str(venv_bin_path / "pip"):
        msg = (
            "cibuildwheel: pip available on PATH doesn't match our installed instance. "
            "If you have modified PATH, ensure that you don't overwrite cibuildwheel's "
            "entry or insert pip above it."
        )
        raise errors.FatalError(msg)
    call("pip", "--version", env=env)

    # Ensure that IPHONEOS_DEPLOYMENT_TARGET is set in the environment
    env.setdefault("IPHONEOS_DEPLOYMENT_TARGET", "13.0")

    log.step("Installing build tools...")
    if build_frontend == "pip":
        # No additional build tools required
        pass
    elif build_frontend == "build":
        call(
            "pip",
            "install",
            "--upgrade",
            "build[virtualenv]",
            *constraint_flags(dependency_constraint),
            env=env,
        )
    else:
        assert_never(build_frontend)

    return target_install_path, env


def build(options: Options, tmp_path: Path) -> None:
    if sys.platform != "darwin":
        msg = "iOS binaries can only be built on macOS"
        raise errors.FatalError(msg)

    python_configurations = get_python_configurations(
        build_selector=options.globals.build_selector,
        architectures=options.globals.architectures,
    )

    if not python_configurations:
        return

    try:
        before_all_options_identifier = python_configurations[0].identifier
        before_all_options = options.build_options(before_all_options_identifier)

        if before_all_options.before_all:
            log.step("Running before_all...")
            env = before_all_options.environment.as_dictionary(prev_environment=os.environ)
            env.setdefault("IPHONEOS_DEPLOYMENT_TARGET", "13.0")
            before_all_prepared = prepare_command(
                before_all_options.before_all,
                project=".",
                package=before_all_options.package_dir,
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            build_frontend = build_options.build_frontend or BuildFrontendConfig("build")
            # uv doesn't support iOS
            if build_frontend.name == "build[uv]":
                msg = "uv doesn't support iOS"
                raise errors.FatalError(msg)

            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"

            constraints_path = build_options.dependency_constraints.get_for_python_version(
                version=config.version, tmp_dir=identifier_tmp_dir
            )

            target_install_path, env = setup_python(
                identifier_tmp_dir / "build",
                python_configuration=config,
                dependency_constraint=constraints_path,
                environment=build_options.environment,
                build_frontend=build_frontend.name,
                xbuild_tools=build_options.xbuild_tools,
            )
            pip_version = get_pip_version(env)

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                log.step_end()
                print(
                    f"\nFound previously built wheel {compatible_wheel.name} "
                    f"that is compatible with {config.identifier}. "
                    "Skipping build step..."
                )
                test_wheel = compatible_wheel
            else:
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build,
                        project=".",
                        package=build_options.package_dir,
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")
                built_wheel_dir.mkdir()

                extra_flags = get_build_frontend_extra_flags(
                    build_frontend, build_options.build_verbosity, build_options.config_settings
                )

                build_env = env.copy()
                build_env["VIRTUALENV_PIP"] = pip_version
                if constraints_path:
                    combine_constraints(build_env, constraints_path, None)

                if build_frontend.name == "pip":
                    # Path.resolve() is needed. Without it pip wheel may try to
                    # fetch package from pypi.org. See
                    # https://github.com/pypa/cibuildwheel/pull/369
                    call(
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        build_options.package_dir.resolve(),
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *extra_flags,
                        env=build_env,
                    )
                elif build_frontend.name == "build":
                    call(
                        "python",
                        "-m",
                        "build",
                        build_options.package_dir,
                        "--wheel",
                        f"--outdir={built_wheel_dir}",
                        *extra_flags,
                        env=build_env,
                    )
                else:
                    assert_never(build_frontend)

                test_wheel = built_wheel = next(built_wheel_dir.glob("*.whl"))

                if built_wheel.name.endswith("none-any.whl"):
                    raise errors.NonPlatformWheelError()

                log.step_end()

            if build_options.test_command and build_options.test_selector(config.identifier):
                if not config.is_simulator:
                    log.step("Skipping tests on non-simulator SDK")
                elif config.arch != os.uname().machine:
                    log.step("Skipping tests on non-native simulator architecture")
                else:
                    test_env = build_options.test_environment.as_dictionary(
                        prev_environment=build_env
                    )

                    if build_options.before_test:
                        before_test_prepared = prepare_command(
                            build_options.before_test,
                            project=".",
                            package=build_options.package_dir,
                        )
                        shell(before_test_prepared, env=test_env)

                    log.step("Setting up test harness...")
                    # Clone the testbed project into the build directory
                    testbed_path = identifier_tmp_dir / "testbed"
                    call(
                        "python",
                        target_install_path / "testbed",
                        "clone",
                        testbed_path,
                        env=test_env,
                    )

                    testbed_app_path = testbed_path / "iOSTestbed" / "app"

                    # Copy the test sources to the testbed app
                    if build_options.test_sources:
                        copy_test_sources(
                            build_options.test_sources,
                            Path.cwd(),
                            testbed_app_path,
                        )
                    else:
                        (testbed_app_path / "test_fail.py").write_text(
                            resources.TEST_FAIL_CWD_FILE.read_text()
                        )

                    log.step("Installing test requirements...")
                    # Install the compiled wheel (with any test extras), plus
                    # the test requirements. Use the --platform tag to force
                    # the installation of iOS wheels; this requires the use of
                    # --only-binary=:all:
                    ios_version = test_env["IPHONEOS_DEPLOYMENT_TARGET"]
                    platform_tag = f"ios_{ios_version.replace('.', '_')}_{config.arch}_{config.sdk}"

                    call(
                        "python",
                        "-m",
                        "pip",
                        "install",
                        "--only-binary=:all:",
                        "--platform",
                        platform_tag,
                        "--target",
                        testbed_path / "iOSTestbed" / "app_packages",
                        f"{test_wheel}{build_options.test_extras}",
                        *build_options.test_requires,
                        env=test_env,
                    )

                    log.step("Running test suite...")

                    # iOS doesn't support placeholders in the test command,
                    # because the source dir isn't visible on the simulator.
                    if (
                        "{project}" in build_options.test_command
                        or "{package}" in build_options.test_command
                    ):
                        msg = unwrap_preserving_paragraphs(
                            f"""
                            iOS tests configured with a test command that uses the "{{project}}" or
                            "{{package}}" placeholder. iOS tests cannot use placeholders, because the
                            source directory is not visible on the simulator.

                            In addition, iOS tests must run as a Python module, so the test command
                            must begin with 'python -m'.

                            Test command: {build_options.test_command!r}
                            """
                        )
                        raise errors.FatalError(msg)

                    test_command_list = shlex.split(build_options.test_command)
                    try:
                        for test_command_parts in split_command(test_command_list):
                            match test_command_parts:
                                case ["python", "-m", *rest]:
                                    final_command = rest
                                case ["pytest", *rest]:
                                    # pytest works exactly the same as a module, so we
                                    # can just run it as a module.
                                    msg = unwrap_preserving_paragraphs(f"""
                                        iOS tests configured with a test command which doesn't start
                                        with 'python -m'. iOS tests must execute python modules - other
                                        entrypoints are not supported.

                                        cibuildwheel will try to execute it as if it started with
                                        'python -m'. If this works, all you need to do is add that to
                                        your test command.

                                        Test command: {build_options.test_command!r}
                                    """)
                                    log.warning(msg)
                                    final_command = ["pytest", *rest]
                                case _:
                                    msg = unwrap_preserving_paragraphs(
                                        f"""
                                            iOS tests configured with a test command which doesn't start
                                            with 'python -m'. iOS tests must execute python modules - other
                                            entrypoints are not supported.

                                            Test command: {build_options.test_command!r}
                                        """
                                    )
                                    raise errors.FatalError(msg)

                            call(
                                "python",
                                testbed_path,
                                "run",
                                *(["--verbose"] if build_options.build_verbosity > 0 else []),
                                "--",
                                *final_command,
                                env=test_env,
                            )
                    except subprocess.CalledProcessError:
                        # catches the first test command failure in the loop,
                        # implementing short-circuiting
                        log.step_end(success=False)
                        log.error(f"Test suite failed on {config.identifier}")
                        sys.exit(1)

                    log.step_end()

            # We're all done here; move it to output (overwrite existing)
            if compatible_wheel is None:
                output_wheel = build_options.output_dir.joinpath(built_wheel.name)
                moved_wheel = move_file(built_wheel, output_wheel)
                if moved_wheel != output_wheel.resolve():
                    log.warning(
                        f"{built_wheel} was moved to {moved_wheel} instead of {output_wheel}"
                    )
                built_wheels.append(output_wheel)

            # Clean up
            shutil.rmtree(identifier_tmp_dir)

            log.build_end()
    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
