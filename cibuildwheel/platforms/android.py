import csv
import hashlib
import os
import platform
import re
import shlex
import shutil
import subprocess
import sysconfig
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from os.path import relpath
from pathlib import Path
from pprint import pprint
from runpy import run_path
from textwrap import dedent
from typing import Any

from build import ProjectBuilder
from build.env import IsolatedEnv
from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from filelock import FileLock

from .. import errors, platforms  # pylint: disable=cyclic-import
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
from ..venv import constraint_flags, find_uv, virtualenv

ANDROID_TRIPLET = {
    "arm64_v8a": "aarch64-linux-android",
    "x86_64": "x86_64-linux-android",
}


def parse_identifier(identifier: str) -> tuple[str, str]:
    match = re.fullmatch(r"cp(\d)(\d+)-android_(.+)", identifier)
    if not match:
        msg = f"invalid Android identifier: '{identifier}'"
        raise ValueError(msg)
    major, minor, arch = match.groups()
    return (f"{major}.{minor}", arch)


def android_triplet(identifier: str) -> str:
    return ANDROID_TRIPLET[parse_identifier(identifier)[1]]


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


@dataclass(frozen=True)
class BuildState:
    config: PythonConfiguration
    options: BuildOptions
    build_path: Path
    python_dir: Path
    build_env: dict[str, str]
    android_env: dict[str, str]


def build(options: Options, tmp_path: Path) -> None:
    if "ANDROID_HOME" not in os.environ:
        msg = (
            "ANDROID_HOME environment variable is not set. For instructions, see "
            "https://cibuildwheel.pypa.io/en/stable/platforms/#android"
        )
        raise errors.FatalError(msg)

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
            build_env, android_env = setup_env(config, build_options, build_path, python_dir)
            state = BuildState(
                config, build_options, build_path, python_dir, build_env, android_env
            )

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                print(
                    f"\nFound previously built wheel {compatible_wheel.name} that is "
                    f"compatible with {config.identifier}. Skipping build step..."
                )
                repaired_wheel = compatible_wheel
            else:
                before_build(state)
                built_wheel = build_wheel(state)
                repaired_wheel = repair_wheel(state, built_wheel)

            test_wheel(state, repaired_wheel, build_frontend=build_options.build_frontend.name)

            output_wheel: Path | None = None
            if compatible_wheel is None:
                output_wheel = move_file(
                    repaired_wheel, build_options.output_dir / repaired_wheel.name
                )
                built_wheels.append(output_wheel)

            shutil.rmtree(build_path)
            log.build_end(output_wheel)

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
    build_frontend = build_options.build_frontend.name
    use_uv = build_frontend == "build[uv]"
    uv_path = find_uv()
    if use_uv and uv_path is None:
        msg = "uv not found"
        raise AssertionError(msg)
    pip = ["pip"] if not use_uv else [str(uv_path), "pip"]

    # Create virtual environment
    python_exe = create_python_build_standalone_environment(
        config.version, build_path, CIBW_CACHE_PATH
    )
    venv_dir = build_path / "venv"
    dependency_constraint = build_options.dependency_constraints.get_for_python_version(
        version=config.version, tmp_dir=build_path
    )
    build_env = virtualenv(
        config.version, python_exe, venv_dir, dependency_constraint, use_uv=use_uv
    )
    create_cmake_toolchain(config, build_path, python_dir, build_env)

    # Apply custom environment variables, and check environment is still valid
    build_env = build_options.environment.as_dictionary(build_env)
    build_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    for command in ["python"] if use_uv else ["python", "pip"]:
        command_path = call("which", command, env=build_env, capture_stdout=True).strip()
        if command_path != f"{venv_dir}/bin/{command}":
            msg = (
                f"{command} available on PATH doesn't match our installed instance. If you "
                f"have modified PATH, ensure that you don't overwrite cibuildwheel's entry "
                f"or insert {command} above it."
            )
            raise errors.FatalError(msg)
        call(command, "--version", env=build_env)

    # Construct an altered environment which simulates running on Android.
    android_env = setup_android_env(config, python_dir, venv_dir, build_env)

    # Install build tools
    if build_frontend not in {"build", "build[uv]"}:
        msg = "Android requires the build frontend to be 'build'"
        raise errors.FatalError(msg)
    call(*pip, "install", "build", *constraint_flags(dependency_constraint), env=build_env)

    # Build-time requirements must be queried within android_env, because
    # `get_requires_for_build` can run arbitrary code in setup.py scripts, which may be
    # affected by the target platform. However, the requirements must be installed
    # within build_env, because they're going to run on the build machine.
    #
    # The `build` CLI doesn't support this combination, so we use its API to query the
    # requirements, and then install them ourselves with pip. We'll later run `build` in
    # the same environment, passing the `--no-isolation` option.
    class AndroidEnv(IsolatedEnv):
        @property
        def python_executable(self) -> str:
            return f"{venv_dir}/bin/python"

        def make_extra_environ(self) -> dict[str, str]:
            return android_env

    pb = ProjectBuilder.from_isolated_env(AndroidEnv(), build_options.package_dir)
    if pb.build_system_requires:
        call(*pip, "install", *pb.build_system_requires, env=build_env)

    requires_for_build = pb.get_requires_for_build(
        "wheel", parse_config_settings(build_options.config_settings)
    )
    if requires_for_build:
        call(*pip, "install", *requires_for_build, env=build_env)

    return build_env, android_env


def create_cmake_toolchain(
    config: PythonConfiguration, build_path: Path, python_dir: Path, build_env: dict[str, str]
) -> None:
    toolchain_path = build_path / "toolchain.cmake"
    build_env["CMAKE_TOOLCHAIN_FILE"] = str(toolchain_path)
    with open(toolchain_path, "w", encoding="UTF-8") as toolchain_file:
        print(
            dedent(
                f"""\
                # To support as many build systems as possible, we use environment
                # variables as the single source of truth for compiler flags and paths,
                # so they don't need to be specified here.

                set(CMAKE_SYSTEM_NAME Android)
                set(CMAKE_SYSTEM_PROCESSOR {android_triplet(config.identifier).split("-")[0]})

                # Inhibit all of CMake's own NDK handling code.
                set(CMAKE_SYSTEM_VERSION 1)

                # Tell CMake where to look for headers and libraries.
                set(CMAKE_FIND_ROOT_PATH "{python_dir}/prefix")
                set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
                set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
                set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
                set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)

                # Allow CMake to run Python in the simulated Android environment when
                # policy CMP0190 is active.
                set(CMAKE_CROSSCOMPILING_EMULATOR /bin/sh -c [["$0" "$@"]])
                """
            ),
            file=toolchain_file,
        )


def localize_sysconfigdata(
    python_dir: Path, build_env: dict[str, str], sysconfigdata_path: Path
) -> dict[str, Any]:
    sysconfigdata: dict[str, Any] = run_path(str(sysconfigdata_path))["build_time_vars"]
    with sysconfigdata_path.open("w", encoding="UTF-8") as f:
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
    config: PythonConfiguration, python_dir: Path, venv_dir: Path, build_env: dict[str, str]
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

    # Activate the code in _cross_venv.py.
    android_env = build_env.copy()
    android_env["CIBW_HOST_TRIPLET"] = android_triplet(config.identifier)

    # Get the environment variables needed to build for Android (CC, CFLAGS, etc). These are
    # generated by https://github.com/python/cpython/blob/main/Android/android-env.sh.
    env_output = call(python_dir / "android.py", "env", env=build_env, capture_stdout=True)

    # shlex.split should produce a sequence alternating between:
    #   * the word "export"
    #   * a key=value string, without quotes
    for i, token in enumerate(shlex.split(env_output)):
        if i % 2 == 0:
            assert token == "export", token
        else:
            key, sep, value = token.partition("=")
            assert sep == "=", token
            android_env[key] = value

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


def before_build(state: BuildState) -> None:
    if state.options.before_build:
        log.step("Running before_build...")
        shell_prepared(
            state.options.before_build,
            build_options=state.options,
            env=state.build_env,
        )


def build_wheel(state: BuildState) -> Path:
    log.step("Building wheel...")
    built_wheel_dir = state.build_path / "built_wheel"
    call(
        "python",
        "-m",
        "build",
        state.options.package_dir,
        "--wheel",
        "--no-isolation",
        "--skip-dependency-check",
        f"--outdir={built_wheel_dir}",
        *get_build_frontend_extra_flags(
            state.options.build_frontend,
            state.options.build_verbosity,
            state.options.config_settings,
        ),
        env=state.android_env,
    )

    built_wheels = list(built_wheel_dir.glob("*.whl"))
    if len(built_wheels) != 1:
        msg = f"{built_wheel_dir} contains {len(built_wheels)} wheels; expected 1"
        raise errors.FatalError(msg)
    built_wheel = built_wheels[0]

    if built_wheel.name.endswith("none-any.whl"):
        raise errors.NonPlatformWheelError()
    return built_wheel


def repair_wheel(state: BuildState, built_wheel: Path) -> Path:
    log.step("Repairing wheel...")
    repaired_wheel_dir = state.build_path / "repaired_wheel"
    repaired_wheel_dir.mkdir()

    if state.options.repair_command:
        shell(
            prepare_command(
                state.options.repair_command,
                wheel=built_wheel,
                dest_dir=repaired_wheel_dir,
                package=state.options.package_dir,
                project=".",
            ),
            env=state.build_env,
        )
    else:
        repair_default(state.android_env, built_wheel, repaired_wheel_dir)

    repaired_wheels = list(repaired_wheel_dir.glob("*.whl"))
    if len(repaired_wheels) == 0:
        raise errors.RepairStepProducedNoWheelError()
    if len(repaired_wheels) != 1:
        msg = f"{repaired_wheel_dir} contains {len(repaired_wheels)} wheels; expected 1"
        raise errors.FatalError(msg)
    repaired_wheel = repaired_wheels[0]

    if repaired_wheel.name.endswith("none-any.whl"):
        raise errors.NonPlatformWheelError()
    return repaired_wheel


def repair_default(
    android_env: dict[str, str], built_wheel: Path, repaired_wheel_dir: Path
) -> None:
    """
    Adds libc++ to the wheel if anything links against it. In the future this should be
    moved to auditwheel and generalized to support more libraries.
    """
    if (match := re.search(r"^(.+?)-", built_wheel.name)) is None:
        msg = f"Failed to parse wheel filename: {built_wheel.name}"
        raise errors.FatalError(msg)
    wheel_name = match[1]

    unpacked_dir = repaired_wheel_dir / "unpacked"
    unpacked_dir.mkdir()
    shutil.unpack_archive(built_wheel, unpacked_dir, format="zip")

    # Some build systems are inconsistent about name normalization, so don't assume the
    # dist-info name is identical to the wheel name.
    record_paths = list(unpacked_dir.glob("*.dist-info/RECORD"))
    if len(record_paths) != 1:
        msg = f"{built_wheel.name} contains {len(record_paths)} dist-info/RECORD files; expected 1"
        raise errors.FatalError(msg)

    old_soname = "libc++_shared.so"
    paths_to_patch = []
    for path, elffile in elf_file_filter(
        unpacked_dir / filename
        for filename, *_ in csv.reader(record_paths[0].read_text().splitlines())
    ):
        if (dynamic := elffile.get_section_by_name(".dynamic")) and any(  # type: ignore[no-untyped-call]
            tag.entry.d_tag == "DT_NEEDED" and tag.needed == old_soname
            for tag in dynamic.iter_tags()
        ):
            paths_to_patch.append(path)

    if not paths_to_patch:
        shutil.copyfile(built_wheel, repaired_wheel_dir / built_wheel.name)
    else:
        # Android doesn't support DT_RPATH, but supports DT_RUNPATH since API level 24
        # (https://github.com/aosp-mirror/platform_bionic/blob/master/android-changes-for-ndk-developers.md).
        if int(sysconfig_print('get_config_vars()["ANDROID_API_LEVEL"]', android_env)) < 24:
            msg = f"Adding {old_soname} requires ANDROID_API_LEVEL to be at least 24"
            raise errors.FatalError(msg)

        toolchain = Path(android_env["CC"]).parent.parent
        src_path = toolchain / f"sysroot/usr/lib/{android_env['CIBW_HOST_TRIPLET']}/{old_soname}"

        # Use the same library location as auditwheel would.
        libs_dir = unpacked_dir / (wheel_name + ".libs")
        libs_dir.mkdir()
        new_soname = soname_with_hash(src_path)
        dst_path = libs_dir / new_soname
        shutil.copyfile(src_path, dst_path)
        call(which("patchelf"), "--set-soname", new_soname, dst_path)

        for path in paths_to_patch:
            call(which("patchelf"), "--replace-needed", old_soname, new_soname, path)
            call(
                which("patchelf"),
                "--set-rpath",
                f"${{ORIGIN}}/{relpath(libs_dir, path.parent)}",
                path,
            )
        call(which("wheel"), "pack", unpacked_dir, "-d", repaired_wheel_dir)


# If cibuildwheel was called without activating its environment, its scripts directory
# will not be on the PATH.
def which(cmd: str) -> str:
    scripts_dir = sysconfig.get_path("scripts")
    result = shutil.which(cmd, path=scripts_dir + os.pathsep + os.environ["PATH"])
    if result is None:
        msg = f"Couldn't find {cmd!r} in {scripts_dir} or on the PATH"
        raise errors.FatalError(msg)
    return result


def elf_file_filter(paths: Iterable[Path]) -> Iterator[tuple[Path, ELFFile]]:
    """Filter through an iterator of filenames and load up only ELF files"""
    for path in paths:
        if not path.name.endswith(".py"):
            try:
                with open(path, "rb") as f:
                    candidate = ELFFile(f)  # type: ignore[no-untyped-call]
                    yield path, candidate
            except ELFError:
                pass  # Not an ELF file


def soname_with_hash(src_path: Path) -> str:
    """Return the same library filename as auditwheel would"""
    shorthash = hashlib.sha256(src_path.read_bytes()).hexdigest()[:8]
    src_name = src_path.name
    base, ext = src_name.split(".", 1)
    if not base.endswith(f"-{shorthash}"):
        return f"{base}-{shorthash}.{ext}"
    else:
        return src_name


def test_wheel(state: BuildState, wheel: Path, *, build_frontend: str) -> None:
    test_command = state.options.test_command
    if not (test_command and state.options.test_selector(state.config.identifier)):
        return

    log.step("Testing wheel...")
    use_uv = build_frontend == "build[uv]"
    uv_path = find_uv()
    if use_uv and uv_path is None:
        msg = "uv not found"
        raise AssertionError(msg)
    pip = ["pip"] if not use_uv else [str(uv_path), "pip"]

    native_arch = arch_synonym(platform.machine(), platforms.native_platform(), "android")
    if state.config.arch != native_arch:
        log.warning(
            f"Skipping tests for {state.config.arch}, as the build machine only "
            f"supports {native_arch}"
        )
        return

    if state.options.before_test:
        shell_prepared(
            state.options.before_test,
            build_options=state.options,
            env=state.build_env,
        )

    platform_args = (
        ["--python-platform", android_triplet(state.config.identifier)]
        if use_uv
        else [
            "--platform",
            sysconfig_print("get_platform()", state.android_env).replace("-", "_"),
        ]
    )

    # Install the wheel and test-requires.
    site_packages_dir = state.build_path / "site-packages"
    site_packages_dir.mkdir()
    call(
        *pip,
        "install",
        "--only-binary=:all:",
        *platform_args,
        "--target",
        site_packages_dir,
        f"{wheel}{state.options.test_extras}",
        *state.options.test_requires,
        env=state.android_env,
    )

    # Copy test-sources.
    cwd_dir = state.build_path / "cwd"
    cwd_dir.mkdir()
    if state.options.test_sources:
        copy_test_sources(state.options.test_sources, Path.cwd(), cwd_dir)
    else:
        (cwd_dir / "test_fail.py").write_text(
            resources.TEST_FAIL_CWD_FILE.read_text(),
        )

    # Android doesn't support placeholders in the test command.
    if any(("{" + placeholder + "}") in test_command for placeholder in ["project", "package"]):
        msg = (
            f"Test command {test_command!r} with a "
            "'{project}' or '{package}' placeholder is not supported on Android, "
            "because the source directory is not visible on the emulator."
        )
        raise errors.FatalError(msg)

    # Parse test-command.
    test_args = shlex.split(test_command)
    if test_args[0] in ["python", "python3"] and any(arg in test_args for arg in ["-c", "-m"]):
        # Forward the args to the CPython testbed script. We require '-c' or '-m'
        # to be in the command, because without those flags, the testbed script
        # will prepend '-m test', which will run Python's own test suite.
        del test_args[0]
    elif test_args[0] in ["pytest"]:
        # We transform some commands into the `python -m` form, but this is deprecated.
        msg = (
            f"Test command {test_command!r} is not supported on Android. "
            "cibuildwheel will try to execute it as if it started with 'python -m'. "
            "If this works, all you need to do is add that to your test command."
        )
        log.warning(msg)
        test_args.insert(0, "-m")
    else:
        msg = (
            f"Test command {test_command!r} is not supported on Android. "
            f"Command must begin with 'python' or 'python3', and contain '-m' or '-c'."
        )
        raise errors.FatalError(msg)

    # By default, run on a testbed managed emulator running the newest supported
    # Android version. However, if the user specifies a --managed or --connected
    # test execution argument, that argument takes precedence.
    test_runtime_args = state.options.test_runtime.args

    if any(arg.startswith(("--managed", "--connected")) for arg in test_runtime_args):
        emulator_args = []
    else:
        emulator_args = ["--managed", "maxVersion"]

    # Run the test app.
    call(
        state.python_dir / "android.py",
        "test",
        "--site-packages",
        site_packages_dir,
        "--cwd",
        cwd_dir,
        *emulator_args,
        *(["-v"] if state.options.build_verbosity > 0 else []),
        *test_runtime_args,
        "--",
        *test_args,
        env=state.build_env,
    )


def sysconfig_print(method_call: str, env: dict[str, str]) -> str:
    return call(
        "python",
        "-c",
        f'import sysconfig; print(sysconfig.{method_call}, end="")',
        env=env,
        capture_stdout=True,
    )
