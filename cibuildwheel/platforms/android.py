import os
import platform
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from runpy import run_path
from typing import Any

from build import ProjectBuilder
from build.env import IsolatedEnv
from filelock import FileLock

from .. import errors, platforms
from ..architecture import Architecture, arch_synonym
from ..frontend import get_build_frontend_extra_flags, parse_config_settings
from ..logger import log
from ..options import BuildOptions, Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import CIBW_CACHE_PATH, copy_test_sources, download, move_file
from ..util.helpers import prepare_command
from ..util.packaging import find_compatible_wheel
from ..util.python_build_standalone import create_python_build_standalone_environment
from ..venv import constraint_flags, virtualenv


def android_triplet(identifier: str) -> str:
    return {
        "arm64_v8a": "aarch64-linux-android",
        "x86_64": "x86_64-linux-android",
    }[parse_identifier(identifier)[1]]


def parse_identifier(identifier: str) -> tuple[str, str]:
    match = re.fullmatch(r"cp(\d)(\d+)-android_(.+)", identifier)
    if not match:
        msg = f"invalid Android identifier: '{identifier}'"
        raise ValueError(msg)
    major, minor, arch = match.groups()
    return (f"{major}.{minor}", arch)


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str

    @property
    def arch(self) -> str:
        return parse_identifier(self.identifier)[1]


def all_python_configurations() -> list[PythonConfiguration]:
    return [PythonConfiguration(**item) for item in resources.read_python_configs("android")]


def get_python_configurations(
    build_selector: BuildSelector, architectures: set[Architecture]
) -> list[PythonConfiguration]:
    return [
        c
        for c in all_python_configurations()
        if c.arch in architectures and build_selector(c.identifier)
    ]


def shell_prepared(command: str, *, build_options: BuildOptions, env: dict[str, str]) -> None:
    shell(
        prepare_command(command, project=".", package=build_options.package_dir),
        env=env,
    )


def before_all(options: Options, python_configurations: list[PythonConfiguration]) -> None:
    before_all_options = options.build_options(python_configurations[0].identifier)
    if before_all_options.before_all:
        log.step("Running before_all...")
        shell_prepared(
            before_all_options.before_all,
            build_options=before_all_options,
            env=before_all_options.environment.as_dictionary(os.environ),
        )


def build(options: Options, tmp_path: Path) -> None:
    configs = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )
    if not configs:
        return

    try:
        before_all(options, configs)

        built_wheels: list[Path] = []
        for config in configs:
            log.build_start(config.identifier)
            build_options = options.build_options(config.identifier)
            build_path = tmp_path / config.identifier
            build_path.mkdir()

            python_dir = setup_target_python(config, build_path)

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                print(
                    f"\nFound previously built wheel {compatible_wheel.name} that is "
                    f"compatible with {config.identifier}. Skipping build step..."
                )
                repaired_wheel = compatible_wheel
            else:
                build_env, android_env = setup_env(config, build_options, build_path, python_dir)
                before_build(build_options, build_env)
                repaired_wheel = build_wheel(build_options, build_path, android_env)

            test_wheel(
                config,
                build_options,
                build_path,
                python_dir,
                build_env,
                android_env,
                repaired_wheel,
            )

            if compatible_wheel is None:
                built_wheels.append(
                    move_file(repaired_wheel, build_options.output_dir / repaired_wheel.name)
                )

            shutil.rmtree(build_path)
            log.build_end()

    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error


def setup_target_python(config: PythonConfiguration, build_path: Path) -> Path:
    log.step("Installing target Python...")
    python_tgz = CIBW_CACHE_PATH / config.url.rpartition("/")[-1]
    with FileLock(f"{python_tgz}.lock"):
        if not python_tgz.exists():
            download(config.url, python_tgz)

    python_dir = build_path / "python"
    python_dir.mkdir()
    shutil.unpack_archive(python_tgz, python_dir)
    return python_dir


def setup_env(
    config: PythonConfiguration, build_options: BuildOptions, build_path: Path, python_dir: Path
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Returns two environment dicts, both pointing at the same virtual environment:

    * build_env, which uses the environment normally.
    * android_env, which uses the environment while simulating running on Android.
    """
    log.step("Setting up build environment...")

    # Create virtual environment
    python_exe = create_python_build_standalone_environment(
        config.version, build_path, CIBW_CACHE_PATH
    )
    venv_dir = build_path / "venv"
    dependency_constraint = build_options.dependency_constraints.get_for_python_version(
        version=config.version, tmp_dir=build_path
    )
    build_env = virtualenv(
        config.version, python_exe, venv_dir, dependency_constraint, use_uv=False
    )

    # Apply custom environment variables, and check environment is still valid
    build_env = build_options.environment.as_dictionary(build_env)
    build_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    for command in ["python", "pip"]:
        which = call("which", command, env=build_env, capture_stdout=True).strip()
        if which != f"{venv_dir}/bin/{command}":
            msg = (
                f"{command} available on PATH doesn't match our installed instance. If you "
                f"have modified PATH, ensure that you don't overwrite cibuildwheel's entry "
                f"or insert {command} above it."
            )
            raise errors.FatalError(msg)
        call(command, "--version", env=build_env)

    # Construct an altered environment which simulates running on Android.
    android_env = setup_android_env(python_dir, venv_dir, build_env)

    # Install build tools
    build_frontend = build_options.build_frontend
    if build_frontend.name != "build":
        msg = "Android requires the build frontend to be 'build'"
        raise errors.FatalError(msg)
    call("pip", "install", "build", *constraint_flags(dependency_constraint), env=build_env)

    # Install build-time requirements. These must be installed for the build platform,
    # but queried while simulating Android. The `build` CLI doesn't support this
    # combination, so we use its API to query the requirements, but install them
    # ourselves. We'll later run `build` in the same environment, passing the
    # `--no-isolation` option.
    class AndroidEnv(IsolatedEnv):
        @property
        def python_executable(self) -> str:
            return f"{venv_dir}/bin/python"

        def make_extra_environ(self) -> dict[str, str]:
            return android_env

    pb = ProjectBuilder.from_isolated_env(AndroidEnv(), build_options.package_dir)
    if pb.build_system_requires:
        call("pip", "install", *pb.build_system_requires, env=build_env)

    requires_for_build = pb.get_requires_for_build(
        "wheel", parse_config_settings(build_options.config_settings)
    )
    if requires_for_build:
        call("pip", "install", *requires_for_build, env=build_env)

    return build_env, android_env


def localize_sysconfigdata(
    python_dir: Path, build_env: dict[str, str], sysconfigdata_path: Path
) -> dict[str, Any]:
    sysconfigdata: dict[str, Any] = run_path(str(sysconfigdata_path))["build_time_vars"]
    with sysconfigdata_path.open("w") as f:
        f.write("# Generated by cibuildwheel\n")
        f.write("build_time_vars = ")
        sysconfigdata = localized_vars(build_env, sysconfigdata, python_dir / "prefix")
        pprint(sysconfigdata, stream=f, compact=True)
        return sysconfigdata


def localized_vars(
    build_env: dict[str, str], orig_vars: dict[str, Any], prefix: Path
) -> dict[str, Any]:
    orig_prefix = orig_vars["prefix"]
    localized_vars_ = {}
    for key, value in orig_vars.items():
        # The host's sysconfigdata will include references to build-time paths.
        # Update these to refer to the current prefix.
        final = value
        if isinstance(final, str):
            final = final.replace(orig_prefix, str(prefix))

        if key == "ANDROID_API_LEVEL":
            if api_level := build_env.get(key):
                final = int(api_level)

        # Build systems vary in whether FLAGS variables are read from sysconfig, and if so,
        # whether they're replaced by environment variables or combined with them. Even
        # setuptools has changed its behavior here
        # (https://github.com/pypa/setuptools/issues/4836).
        #
        # Ensure consistency by clearing the sysconfig variables and letting the environment
        # variables take effect alone. This will also work for any non-Python build systems
        # which the build script may call.
        elif key in ["CFLAGS", "CXXFLAGS", "LDFLAGS"]:
            final = ""

        # These variables contain an embedded copy of LDFLAGS.
        elif key in ["LDSHARED", "LDCXXSHARED"]:
            final = final.removesuffix(" " + orig_vars["LDFLAGS"])

        localized_vars_[key] = final

    return localized_vars_


def setup_android_env(
    python_dir: Path, venv_dir: Path, build_env: dict[str, str]
) -> dict[str, str]:
    site_packages = next(venv_dir.glob("lib/python*/site-packages"))
    for suffix in ["pth", "py"]:
        shutil.copy(resources.PATH / f"_cross_venv.{suffix}", site_packages)

    sysconfigdata_path = Path(
        shutil.copy(
            next(python_dir.glob("prefix/lib/python*/_sysconfigdata_*.py")),
            site_packages,
        )
    )
    sysconfigdata = localize_sysconfigdata(python_dir, build_env, sysconfigdata_path)

    android_env = build_env.copy()
    android_env["CIBW_CROSS_VENV"] = "1"  # Activates the code in _cross_venv.py.

    env_output = call(python_dir / "android.py", "env", env=build_env, capture_stdout=True)
    for line in env_output.splitlines():
        key, value = line.removeprefix("export ").split("=", 1)
        value_split = shlex.split(value)
        assert len(value_split) == 1, value_split
        android_env[key] = value_split[0]

    # localized_vars cleared the CFLAGS and CXXFLAGS in the sysconfigdata, but most
    # packages take their optimization flags from these variables. Pass these flags via
    # environment variables instead.
    #
    # We don't enable debug information, because it significantly increases binary size,
    # and most Android app developers don't have the NDK installed, so they would have no
    # way to strip it.
    opt = " ".join(word for word in sysconfigdata["OPT"].split() if not word.startswith("-g"))
    for key in ["CFLAGS", "CXXFLAGS"]:
        android_env[key] += " " + opt

    # Format the environment so it can be pasted into a shell when debugging.
    for key, value in sorted(android_env.items()):
        if os.environ.get(key) != value:
            print(f"export {key}={shlex.quote(value)}")

    return android_env


def before_build(build_options: BuildOptions, env: dict[str, str]) -> None:
    if build_options.before_build:
        log.step("Running before_build...")
        shell_prepared(build_options.before_build, build_options=build_options, env=env)


def build_wheel(build_options: BuildOptions, build_path: Path, android_env: dict[str, str]) -> Path:
    log.step("Building wheel...")
    built_wheel_dir = build_path / "built_wheel"
    call(
        "python",
        "-m",
        "build",
        build_options.package_dir,
        "--wheel",
        "--no-isolation",
        "--skip-dependency-check",
        f"--outdir={built_wheel_dir}",
        *get_build_frontend_extra_flags(
            build_options.build_frontend,
            build_options.build_verbosity,
            build_options.config_settings,
        ),
        env=android_env,
    )

    built_wheels = list(built_wheel_dir.glob("*.whl"))
    if len(built_wheels) != 1:
        msg = f"{built_wheel_dir} contains {len(built_wheels)} wheels; expected 1"
        raise errors.FatalError(msg)
    built_wheel = built_wheels[0]

    if built_wheel.name.endswith("none-any.whl"):
        raise errors.NonPlatformWheelError()
    return built_wheel


# pylint: disable-next=too-many-positional-arguments
def test_wheel(
    config: PythonConfiguration,
    build_options: BuildOptions,
    build_path: Path,
    python_dir: Path,
    build_env: dict[str, str],
    android_env: dict[str, str],
    wheel: Path,
) -> None:
    if not (build_options.test_command and build_options.test_selector(config.identifier)):
        return

    log.step("Testing wheel...")
    native_arch = arch_synonym(platform.machine(), platforms.native_platform(), "android")
    if config.arch != native_arch:
        log.warning(
            f"Skipping tests for {config.arch}, as the build machine only supports {native_arch}"
        )
        return

    if build_options.before_test:
        shell_prepared(build_options.before_test, build_options=build_options, env=build_env)

    # Install the wheel and test-requires.
    platform_tag = (
        call(
            "python",
            "-c",
            "import sysconfig; print(sysconfig.get_platform())",
            env=android_env,
            capture_stdout=True,
        )
        .strip()
        .replace("-", "_")
    )

    site_packages_dir = build_path / "site-packages"
    site_packages_dir.mkdir()
    call(
        "pip",
        "install",
        "--only-binary=:all:",
        "--platform",
        platform_tag,
        "--target",
        site_packages_dir,
        f"{wheel}{build_options.test_extras}",
        *build_options.test_requires,
        env=build_env,
    )

    # Copy test-sources.
    cwd_dir = build_path / "cwd"
    cwd_dir.mkdir()
    if build_options.test_sources:
        copy_test_sources(build_options.test_sources, Path.cwd(), cwd_dir)
    else:
        (cwd_dir / "test_fail.py").write_text(
            resources.TEST_FAIL_CWD_FILE.read_text(),
        )

    # Android doesn't support placeholders in the test command.
    if any(
        ("{" + placeholder + "}") in build_options.test_command
        for placeholder in ["project", "package"]
    ):
        msg = (
            f"Test command '{build_options.test_command}' with a "
            "'{project}' or '{package}' placeholder is not supported on Android, "
            "because the source directory is not visible on the emulator."
        )
        raise errors.FatalError(msg)

    # Parse test-command.
    test_args = shlex.split(build_options.test_command)
    if test_args[:2] in [["python", "-c"], ["python", "-m"]]:
        test_args[:3] = [test_args[1], test_args[2], "--"]
    elif test_args[0] in ["pytest"]:
        test_args[:1] = ["-m", test_args[0], "--"]
    else:
        msg = (
            f"Test command '{build_options.test_command}' is not supported on "
            f"Android. Supported commands are 'python -m', 'python -c' and 'pytest'."
        )
        raise errors.FatalError(msg)

    # Run the test app.
    call(
        python_dir / "android.py",
        "test",
        "--managed",
        "maxVersion",
        "--site-packages",
        site_packages_dir,
        "--cwd",
        cwd_dir,
        *test_args,
        env=build_env,
    )
