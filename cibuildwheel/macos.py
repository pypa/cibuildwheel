from __future__ import annotations

import functools
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple, cast

from filelock import FileLock

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .options import Options
from .typing import Literal, PathOrStr, assert_never
from .util import (
    CIBW_CACHE_PATH,
    AlreadyBuiltWheelError,
    BuildFrontend,
    BuildSelector,
    NonPlatformWheelError,
    call,
    detect_ci_provider,
    download,
    find_compatible_wheel,
    get_build_verbosity_extra_flags,
    get_pip_version,
    install_certifi_script,
    prepare_command,
    read_python_configs,
    shell,
    split_config_settings,
    unwrap,
    virtualenv,
)


def get_macos_version() -> tuple[int, int]:
    """
    Returns the macOS major/minor version, as a tuple, e.g. (10, 15) or (11, 0)

    These tuples can be used in comparisons, e.g.
        (10, 14) <= (11, 0) == True
        (10, 14) <= (10, 16) == True
        (11, 2) <= (11, 0) != True
    """
    version_str, _, _ = platform.mac_ver()
    version = tuple(map(int, version_str.split(".")[:2]))
    return cast(Tuple[int, int], version)


def get_macos_sdks() -> list[str]:
    output = call("xcodebuild", "-showsdks", capture_stdout=True)
    return [m.group(1) for m in re.finditer(r"-sdk (macosx\S+)", output)]


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str


def get_python_configurations(
    build_selector: BuildSelector, architectures: set[Architecture]
) -> list[PythonConfiguration]:

    full_python_configs = read_python_configs("macos")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    # filter out configs that don't match any of the selected architectures
    python_configurations = [
        c
        for c in python_configurations
        if any(c.identifier.endswith(a.value) for a in architectures)
    ]

    # skip builds as required by BUILD/SKIP
    return [c for c in python_configurations if build_selector(c.identifier)]


def install_cpython(tmp: Path, version: str, url: str) -> Path:
    installation_path = Path(f"/Library/Frameworks/Python.framework/Versions/{version}")
    with FileLock(CIBW_CACHE_PATH / f"cpython{version}.lock"):
        installed_system_packages = call("pkgutil", "--pkgs", capture_stdout=True).splitlines()
        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = f"org.python.Python.PythonFramework-{version}"
        if python_package_identifier not in installed_system_packages:
            if detect_ci_provider() is None:
                # if running locally, we don't want to install CPython with sudo
                # let the user know & provide a link to the installer
                print(
                    f"Error: CPython {version} is not installed.\n"
                    "cibuildwheel will not perform system-wide installs when running outside of CI.\n"
                    f"To build locally, install CPython {version} on this machine, or, disable this version of Python using CIBW_SKIP=cp{version.replace('.', '')}-macosx_*\n"
                    f"\nDownload link: {url}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            pkg_path = tmp / "Python.pkg"
            # download the pkg
            download(url, pkg_path)
            # install
            call("sudo", "installer", "-pkg", pkg_path, "-target", "/")
            pkg_path.unlink()
            env = os.environ.copy()
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
            call(installation_path / "bin" / "python3", install_certifi_script, env=env)

    return installation_path / "bin" / "python3"


def install_pypy(tmp: Path, url: str) -> Path:
    pypy_tar_bz2 = url.rsplit("/", 1)[-1]
    extension = ".tar.bz2"
    assert pypy_tar_bz2.endswith(extension)
    installation_path = CIBW_CACHE_PATH / pypy_tar_bz2[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            downloaded_tar_bz2 = tmp / pypy_tar_bz2
            download(url, downloaded_tar_bz2)
            installation_path.parent.mkdir(parents=True, exist_ok=True)
            call("tar", "-C", installation_path.parent, "-xf", downloaded_tar_bz2)
            downloaded_tar_bz2.unlink()
    return installation_path / "bin" / "pypy3"


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    dependency_constraint_flags: Sequence[PathOrStr],
    environment: ParsedEnvironment,
    build_frontend: BuildFrontend,
) -> dict[str, str]:
    tmp.mkdir()
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        base_python = install_cpython(tmp, python_configuration.version, python_configuration.url)
    elif implementation_id.startswith("pp"):
        base_python = install_pypy(tmp, python_configuration.url)
    else:
        msg = "Unknown Python implementation"
        raise ValueError(msg)
    assert base_python.exists()

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(base_python, venv_path, dependency_constraint_flags)
    venv_bin_path = venv_path / "bin"
    assert venv_bin_path.exists()
    # Fix issue with site.py setting the wrong `sys.prefix`, `sys.exec_prefix`,
    # `sys.path`, ... for PyPy: https://foss.heptapod.net/pypy/pypy/issues/3175
    # Also fix an issue with the shebang of installed scripts inside the
    # testing virtualenv- see https://github.com/theacodes/nox/issues/44 and
    # https://github.com/pypa/virtualenv/issues/620
    # Also see https://github.com/python/cpython/pull/9516
    env.pop("__PYVENV_LAUNCHER__", None)

    # we version pip ourselves, so we don't care about pip version checking
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip'
    call(
        "python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        *dependency_constraint_flags,
        env=env,
        cwd=venv_path,
    )

    # Apply our environment after pip is ready
    env = environment.as_dictionary(prev_environment=env)

    # check what pip version we're on
    assert (venv_bin_path / "pip").exists()
    call("which", "pip", env=env)
    call("pip", "--version", env=env)
    which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
    if which_pip != str(venv_bin_path / "pip"):
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # check what Python version we're on
    call("which", "python", env=env)
    call("python", "--version", env=env)
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    if which_python != str(venv_bin_path / "python"):
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Set MACOSX_DEPLOYMENT_TARGET to 10.9, if the user didn't set it.
    # PyPy defaults to 10.7, causing inconsistencies if it's left unset.
    env.setdefault("MACOSX_DEPLOYMENT_TARGET", "10.9")

    config_is_arm64 = python_configuration.identifier.endswith("arm64")
    config_is_universal2 = python_configuration.identifier.endswith("universal2")

    if python_configuration.version not in {"3.6", "3.7"}:
        if config_is_arm64:
            # macOS 11 is the first OS with arm64 support, so the wheels
            # have that as a minimum.
            env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-11.0-arm64")
            env.setdefault("ARCHFLAGS", "-arch arm64")
        elif config_is_universal2:
            env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-10.9-universal2")
            env.setdefault("ARCHFLAGS", "-arch arm64 -arch x86_64")
        elif python_configuration.identifier.endswith("x86_64"):
            # even on the macos11.0 Python installer, on the x86_64 side it's
            # compatible back to 10.9.
            env.setdefault("_PYTHON_HOST_PLATFORM", "macosx-10.9-x86_64")
            env.setdefault("ARCHFLAGS", "-arch x86_64")

    building_arm64 = config_is_arm64 or config_is_universal2
    if building_arm64 and get_macos_version() < (10, 16) and "SDKROOT" not in env:
        # xcode 12.2 or higher can build arm64 on macos 10.15 or below, but
        # needs the correct SDK selected.
        sdks = get_macos_sdks()

        # Different versions of Xcode contain different SDK versions...
        # we're happy with anything newer than macOS 11.0
        arm64_compatible_sdks = [s for s in sdks if not s.startswith("macosx10.")]

        if not arm64_compatible_sdks:
            log.warning(
                unwrap(
                    """
                    SDK for building arm64-compatible wheels not found. You need Xcode 12.2 or later
                    to build universal2 or arm64 wheels.
                    """
                )
            )
        else:
            env.setdefault("SDKROOT", arm64_compatible_sdks[0])

    log.step("Installing build tools...")
    if build_frontend == "pip":
        call(
            "pip",
            "install",
            "--upgrade",
            "setuptools",
            "wheel",
            "delocate",
            *dependency_constraint_flags,
            env=env,
        )
    elif build_frontend == "build":
        call(
            "pip",
            "install",
            "--upgrade",
            "delocate",
            "build[virtualenv]",
            *dependency_constraint_flags,
            env=env,
        )
    else:
        assert_never(build_frontend)

    return env


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    if len(python_configurations) == 0:
        return

    try:
        before_all_options_identifier = python_configurations[0].identifier
        before_all_options = options.build_options(before_all_options_identifier)

        if before_all_options.before_all:
            log.step("Running before_all...")
            env = before_all_options.environment.as_dictionary(prev_environment=os.environ)
            env.setdefault("MACOSX_DEPLOYMENT_TARGET", "10.9")
            before_all_prepared = prepare_command(
                before_all_options.before_all, project=".", package=before_all_options.package_dir
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"

            config_is_arm64 = config.identifier.endswith("arm64")
            config_is_universal2 = config.identifier.endswith("universal2")

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if build_options.dependency_constraints:
                dependency_constraint_flags = [
                    "-c",
                    build_options.dependency_constraints.get_for_python_version(config.version),
                ]

            env = setup_python(
                identifier_tmp_dir / "build",
                config,
                dependency_constraint_flags,
                build_options.environment,
                build_options.build_frontend,
            )

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                log.step_end()
                print(
                    f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with {config.identifier}. Skipping build step..."
                )
                repaired_wheel = compatible_wheel
            else:
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build, project=".", package=build_options.package_dir
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")
                built_wheel_dir.mkdir()

                verbosity_flags = get_build_verbosity_extra_flags(build_options.build_verbosity)
                extra_flags = split_config_settings(build_options.config_settings)

                if build_options.build_frontend == "pip":
                    extra_flags += verbosity_flags
                    # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                    # see https://github.com/pypa/cibuildwheel/pull/369
                    call(
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        build_options.package_dir.resolve(),
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *extra_flags,
                        env=env,
                    )
                elif build_options.build_frontend == "build":
                    verbosity_setting = " ".join(verbosity_flags)
                    extra_flags += (f"--config-setting={verbosity_setting}",)
                    build_env = env.copy()
                    if build_options.dependency_constraints:
                        constraint_path = (
                            build_options.dependency_constraints.get_for_python_version(
                                config.version
                            )
                        )
                        build_env["PIP_CONSTRAINT"] = constraint_path.as_uri()
                    build_env["VIRTUALENV_PIP"] = get_pip_version(env)
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
                    assert_never(build_options.build_frontend)

                built_wheel = next(built_wheel_dir.glob("*.whl"))

                repaired_wheel_dir.mkdir()

                if built_wheel.name.endswith("none-any.whl"):
                    raise NonPlatformWheelError()

                if build_options.repair_command:
                    log.step("Repairing wheel...")

                    if config_is_universal2:
                        delocate_archs = "x86_64,arm64"
                    elif config_is_arm64:
                        delocate_archs = "arm64"
                    else:
                        delocate_archs = "x86_64"

                    repair_command_prepared = prepare_command(
                        build_options.repair_command,
                        wheel=built_wheel,
                        dest_dir=repaired_wheel_dir,
                        delocate_archs=delocate_archs,
                    )
                    shell(repair_command_prepared, env=env)
                else:
                    shutil.move(str(built_wheel), repaired_wheel_dir)

                repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise AlreadyBuiltWheelError(repaired_wheel.name)

                log.step_end()

            if build_options.test_command and build_options.test_selector(config.identifier):
                machine_arch = platform.machine()
                testing_archs: list[Literal["x86_64", "arm64"]]

                if config_is_arm64:
                    testing_archs = ["arm64"]
                elif config_is_universal2:
                    testing_archs = ["x86_64", "arm64"]
                else:
                    testing_archs = ["x86_64"]

                for testing_arch in testing_archs:
                    if config_is_universal2:
                        arch_specific_identifier = f"{config.identifier}:{testing_arch}"
                        if not build_options.test_selector(arch_specific_identifier):
                            continue

                    if machine_arch == "x86_64" and testing_arch == "arm64":
                        if config_is_arm64:
                            log.warning(
                                unwrap(
                                    """
                                    While arm64 wheels can be built on x86_64, they cannot be
                                    tested. The ability to test the arm64 wheels will be added in a
                                    future release of cibuildwheel, once Apple Silicon CI runners
                                    are widely available. To silence this warning, set
                                    `CIBW_TEST_SKIP: *-macosx_arm64`.
                                    """
                                )
                            )
                        elif config_is_universal2:
                            log.warning(
                                unwrap(
                                    """
                                    While universal2 wheels can be built on x86_64, the arm64 part
                                    of them cannot currently be tested. The ability to test the
                                    arm64 part of a universal2 wheel will be added in a future
                                    release of cibuildwheel, once Apple Silicon CI runners are
                                    widely available. To silence this warning, set
                                    `CIBW_TEST_SKIP: *-macosx_universal2:arm64`.
                                    """
                                )
                            )
                        else:
                            msg = "unreachable"
                            raise RuntimeError(msg)

                        # skip this test
                        continue

                    if testing_arch == "arm64" and config.identifier.startswith("cp38-"):
                        log.warning(
                            unwrap(
                                """
                                While cibuildwheel can build CPython 3.8 universal2/arm64 wheels, we
                                cannot test the arm64 part of them, even when running on an Apple
                                Silicon machine. This is because we use the x86_64 installer of
                                CPython 3.8. See the discussion in
                                https://github.com/pypa/cibuildwheel/pull/1169 for the details. To
                                silence this warning, set `CIBW_TEST_SKIP: cp38-macosx_*:arm64`.
                                """
                            )
                        )

                        # skip this test
                        continue

                    log.step(
                        "Testing wheel..."
                        if testing_arch == machine_arch
                        else f"Testing wheel on {testing_arch}..."
                    )

                    # set up a virtual environment to install and test from, to make sure
                    # there are no dependencies that were pulled in at build time.
                    call("pip", "install", "virtualenv", *dependency_constraint_flags, env=env)

                    venv_dir = identifier_tmp_dir / "venv-test"

                    arch_prefix = []
                    if testing_arch != machine_arch:
                        if machine_arch == "arm64" and testing_arch == "x86_64":
                            # rosetta2 will provide the emulation with just the arch prefix.
                            arch_prefix = ["arch", "-x86_64"]
                        else:
                            msg = f"don't know how to emulate {testing_arch} on {machine_arch}"
                            raise RuntimeError(msg)

                    # define a custom 'call' function that adds the arch prefix each time
                    call_with_arch = functools.partial(call, *arch_prefix)
                    shell_with_arch = functools.partial(call, *arch_prefix, "/bin/sh", "-c")

                    # Use --no-download to ensure determinism by using seed libraries
                    # built into virtualenv
                    call_with_arch("python", "-m", "virtualenv", "--no-download", venv_dir, env=env)

                    virtualenv_env = env.copy()
                    virtualenv_env["PATH"] = os.pathsep.join(
                        [
                            str(venv_dir / "bin"),
                            virtualenv_env["PATH"],
                        ]
                    )

                    # check that we are using the Python from the virtual environment
                    call_with_arch("which", "python", env=virtualenv_env)

                    if build_options.before_test:
                        before_test_prepared = prepare_command(
                            build_options.before_test,
                            project=".",
                            package=build_options.package_dir,
                        )
                        shell_with_arch(before_test_prepared, env=virtualenv_env)

                    # install the wheel
                    call_with_arch(
                        "pip",
                        "install",
                        f"{repaired_wheel}{build_options.test_extras}",
                        env=virtualenv_env,
                    )

                    # test the wheel
                    if build_options.test_requires:
                        call_with_arch(
                            "pip", "install", *build_options.test_requires, env=virtualenv_env
                        )

                    # run the tests from $HOME, with an absolute path in the command
                    # (this ensures that Python runs the tests against the installed wheel
                    # and not the repo code)
                    test_command_prepared = prepare_command(
                        build_options.test_command,
                        project=Path(".").resolve(),
                        package=build_options.package_dir.resolve(),
                    )
                    shell_with_arch(
                        test_command_prepared, cwd=os.environ["HOME"], env=virtualenv_env
                    )

            # we're all done here; move it to output (overwrite existing)
            if compatible_wheel is None:
                try:
                    (build_options.output_dir / repaired_wheel.name).unlink()
                except FileNotFoundError:
                    pass

                shutil.move(str(repaired_wheel), build_options.output_dir)
                built_wheels.append(build_options.output_dir / repaired_wheel.name)

            # clean up
            shutil.rmtree(identifier_tmp_dir)

            log.build_end()
    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
