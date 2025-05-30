import dataclasses
import functools
import inspect
import os
import platform
import re
import shutil
import subprocess
import sys
import typing
from collections.abc import Set
from pathlib import Path
from typing import Literal, assert_never

from filelock import FileLock
from packaging.version import Version

from .. import errors
from ..architecture import Architecture
from ..ci import detect_ci_provider
from ..environment import ParsedEnvironment
from ..frontend import BuildFrontendConfig, BuildFrontendName, get_build_frontend_extra_flags
from ..logger import log
from ..options import Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import (
    CIBW_CACHE_PATH,
    copy_test_sources,
    download,
    move_file,
)
from ..util.helpers import prepare_command, unwrap
from ..util.packaging import combine_constraints, find_compatible_wheel, get_pip_version
from ..venv import constraint_flags, find_uv, virtualenv


@functools.cache
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
    if (10, 15) < version < (11, 0):
        # When built against an older macOS SDK, Python will report macOS 10.16
        # instead of the real version.
        version_str = call(
            sys.executable,
            "-sS",
            "-c",
            "import platform; print(platform.mac_ver()[0])",
            env={"SYSTEM_VERSION_COMPAT": "0"},
            capture_stdout=True,
        )
        version = tuple(map(int, version_str.split(".")[:2]))
    return typing.cast(tuple[int, int], version)


@functools.cache
def get_test_macosx_deployment_target() -> str:
    version = get_macos_version()
    if version >= (11, 0):
        return f"{version[0]}.0"
    return f"{version[0]}.{version[1]}"


def get_macos_sdks() -> list[str]:
    output = call("xcodebuild", "-showsdks", capture_stdout=True)
    return [m.group(1) for m in re.finditer(r"-sdk (macosx\S+)", output)]


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str


def all_python_configurations() -> list[PythonConfiguration]:
    config_dicts = resources.read_python_configs("macos")
    return [PythonConfiguration(**item) for item in config_dicts]


def get_python_configurations(
    build_selector: BuildSelector, architectures: Set[Architecture]
) -> list[PythonConfiguration]:
    python_configurations = all_python_configurations()

    # filter out configs that don't match any of the selected architectures
    python_configurations = [
        c
        for c in python_configurations
        if any(c.identifier.endswith(a.value) for a in architectures)
    ]

    # skip builds as required by BUILD/SKIP
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]

    # filter-out some cross-compilation configs with PyPy and GraalPy:
    # can't build arm64 on x86_64
    # rosetta allows to build x86_64 on arm64
    if platform.machine() == "x86_64":
        python_configurations_before = set(python_configurations)
        python_configurations = [
            c
            for c in python_configurations
            if not (c.identifier.startswith(("pp", "gp")) and c.identifier.endswith("arm64"))
        ]
        removed_elements = python_configurations_before - set(python_configurations)
        if removed_elements:
            ids = ", ".join(c.identifier for c in removed_elements)
            log.quiet(
                unwrap(
                    f"""
                    Note: {ids}  {"was" if len(removed_elements) == 1 else "were"}
                    selected, but can't be built on x86_64 so will be skipped automatically.
                    """
                )
            )

    return python_configurations


def install_cpython(_tmp: Path, version: str, url: str, free_threading: bool) -> Path:
    ft = "T" if free_threading else ""
    installation_path = Path(f"/Library/Frameworks/Python{ft}.framework/Versions/{version}")
    with FileLock(CIBW_CACHE_PATH / f"cpython{version}.lock"):
        installed_system_packages = call("pkgutil", "--pkgs", capture_stdout=True).splitlines()
        # if this version of python isn't installed, get it from python.org and install
        python_package_identifier = f"org.python.Python.Python{ft}Framework-{version}"
        if python_package_identifier not in installed_system_packages:
            if detect_ci_provider() is None:
                # if running locally, we don't want to install CPython with sudo
                # let the user know & provide a link to the installer
                msg = inspect.cleandoc(
                    f"""
                        Error: CPython {version} is not installed.
                        cibuildwheel will not perform system-wide installs when running outside of CI.
                        To build locally, install CPython {version} on this machine, or, disable this
                        version of Python using CIBW_SKIP=cp{version.replace(".", "")}-macosx_*
                        For portable builds, cibuildwheel needs the official builds from python.org.
                        Download link: {url}
                    """
                )
                raise errors.FatalError(msg)
            python_filename = url.split("/")[-1]
            pkg_path = CIBW_CACHE_PATH / "cpython-installer" / python_filename
            if not pkg_path.exists():
                download(url, pkg_path)
            args = []
            if version.startswith("3.13"):
                # Python 3.13 is the first version to have a free-threading option
                args += ["-applyChoiceChangesXML", str(resources.FREE_THREAD_ENABLE_313.resolve())]
            elif version.startswith("3.14"):
                args += ["-applyChoiceChangesXML", str(resources.FREE_THREAD_ENABLE_314.resolve())]
            call("sudo", "installer", "-pkg", pkg_path, *args, "-target", "/")
            pkg_path.unlink()
            env = os.environ.copy()
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

            if free_threading:
                call(installation_path / f"bin/python{version}t", "-m", "ensurepip", env=env)
                call(
                    installation_path / f"bin/python{version}t",
                    resources.INSTALL_CERTIFI_SCRIPT,
                    env=env,
                )
            else:
                call(installation_path / "bin/python3", resources.INSTALL_CERTIFI_SCRIPT, env=env)

    return installation_path / "bin" / (f"python{version}t" if free_threading else "python3")


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


def install_graalpy(tmp: Path, url: str) -> Path:
    graalpy_archive = url.rsplit("/", 1)[-1]
    extension = ".tar.gz"
    assert graalpy_archive.endswith(extension)
    installation_path = CIBW_CACHE_PATH / graalpy_archive[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            downloaded_archive = tmp / graalpy_archive
            download(url, downloaded_archive)
            installation_path.mkdir(parents=True)
            # GraalPy top-folder name is inconsistent with archive name
            call("tar", "-C", installation_path, "--strip-components=1", "-xzf", downloaded_archive)
            downloaded_archive.unlink()
    return installation_path / "bin" / "graalpy"


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    dependency_constraint: Path | None,
    environment: ParsedEnvironment,
    build_frontend: BuildFrontendName,
) -> tuple[Path, dict[str, str]]:
    uv_path = find_uv()
    use_uv = build_frontend == "build[uv]"

    tmp.mkdir()
    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        free_threading = "t-macos" in python_configuration.identifier
        base_python = install_cpython(
            tmp, python_configuration.version, python_configuration.url, free_threading
        )

    elif implementation_id.startswith("pp"):
        base_python = install_pypy(tmp, python_configuration.url)
    elif implementation_id.startswith("gp"):
        base_python = install_graalpy(tmp, python_configuration.url)
    else:
        msg = "Unknown Python implementation"
        raise ValueError(msg)
    assert base_python.exists(), (
        f"{base_python.name} not found, has {list(base_python.parent.iterdir())}"
    )

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(
        python_configuration.version,
        base_python,
        venv_path,
        dependency_constraint,
        use_uv=use_uv,
    )
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

    # Apply our environment after pip is ready
    env = environment.as_dictionary(prev_environment=env)

    # check what Python version we're on
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    print(which_python)
    if which_python != str(venv_bin_path / "python"):
        msg = "python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it."
        raise errors.FatalError(msg)
    call("python", "--version", env=env)

    # check what pip version we're on
    if not use_uv:
        assert (venv_bin_path / "pip").exists()
        which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
        print(which_pip)
        if which_pip != str(venv_bin_path / "pip"):
            msg = "pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it."
            raise errors.FatalError(msg)
        call("pip", "--version", env=env)

    config_is_arm64 = python_configuration.identifier.endswith("arm64")
    config_is_universal2 = python_configuration.identifier.endswith("universal2")

    # Set MACOSX_DEPLOYMENT_TARGET, if the user didn't set it.
    # For arm64, the minimal deployment target is 11.0.
    # On x86_64 (or universal2), use 10.9 as a default.
    # CPython 3.12.6+ needs 10.13.
    if config_is_arm64:
        default_target = "11.0"
    elif Version(python_configuration.version) >= Version("3.12"):
        default_target = "10.13"
    elif python_configuration.identifier.startswith("pp") and Version(
        python_configuration.version
    ) >= Version("3.9"):
        default_target = "10.15"
    else:
        default_target = "10.9"
    env.setdefault("MACOSX_DEPLOYMENT_TARGET", default_target)

    # This is a floor, it can't be set lower than the default_target.
    if Version(env["MACOSX_DEPLOYMENT_TARGET"]) < Version(default_target):
        log.warning(
            f"Bumping MACOSX_DEPLOYMENT_TARGET ({env['MACOSX_DEPLOYMENT_TARGET']}) to the minimum required ({default_target})."
        )
        env["MACOSX_DEPLOYMENT_TARGET"] = default_target

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
            "delocate",
            *constraint_flags(dependency_constraint),
            env=env,
        )
    elif build_frontend == "build":
        call(
            "pip",
            "install",
            "--upgrade",
            "delocate",
            "build[virtualenv]",
            *constraint_flags(dependency_constraint),
            env=env,
        )
    elif build_frontend == "build[uv]":
        assert uv_path is not None
        call(
            uv_path,
            "pip",
            "install",
            "--upgrade",
            "delocate",
            "build[virtualenv, uv]",
            *constraint_flags(dependency_constraint),
            env=env,
        )
    else:
        assert_never(build_frontend)

    return base_python, env


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    if not python_configurations:
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
            build_frontend = build_options.build_frontend or BuildFrontendConfig("build")
            use_uv = build_frontend.name == "build[uv]"
            uv_path = find_uv()
            if use_uv and uv_path is None:
                msg = "uv not found"
                raise AssertionError(msg)
            pip = ["pip"] if not use_uv else [str(uv_path), "pip"]
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"

            config_is_arm64 = config.identifier.endswith("arm64")
            config_is_universal2 = config.identifier.endswith("universal2")

            constraints_path = build_options.dependency_constraints.get_for_python_version(
                version=config.version, tmp_dir=identifier_tmp_dir
            )

            base_python, env = setup_python(
                identifier_tmp_dir / "build",
                config,
                constraints_path,
                build_options.environment,
                build_frontend.name,
            )
            pip_version = None if use_uv else get_pip_version(env)

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

                extra_flags = get_build_frontend_extra_flags(
                    build_frontend, build_options.build_verbosity, build_options.config_settings
                )

                build_env = env.copy()
                if pip_version is not None:
                    build_env["VIRTUALENV_PIP"] = pip_version
                if constraints_path:
                    combine_constraints(
                        build_env, constraints_path, identifier_tmp_dir if use_uv else None
                    )

                if build_frontend.name == "pip":
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
                        env=build_env,
                    )
                elif build_frontend.name == "build" or build_frontend.name == "build[uv]":
                    if use_uv and "--no-isolation" not in extra_flags and "-n" not in extra_flags:
                        extra_flags.append("--installer=uv")
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

                built_wheel = next(built_wheel_dir.glob("*.whl"))

                repaired_wheel_dir.mkdir()

                if built_wheel.name.endswith("none-any.whl"):
                    raise errors.NonPlatformWheelError()

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

                try:
                    repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))
                except StopIteration:
                    raise errors.RepairStepProducedNoWheelError() from None

                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise errors.AlreadyBuiltWheelError(repaired_wheel.name)

                log.step_end()

            if build_options.test_command and build_options.test_selector(config.identifier):
                machine_arch = platform.machine()
                python_arch = call(
                    "python",
                    "-sSc",
                    "import platform; print(platform.machine())",
                    env=env,
                    capture_stdout=True,
                ).strip()
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
                                    tested. Consider building arm64 wheels natively, if your CI
                                    provider offers this. To silence this warning, set
                                    `CIBW_TEST_SKIP: "*-macosx_arm64"`.
                                    """
                                )
                            )
                        elif config_is_universal2:
                            log.warning(
                                unwrap(
                                    """
                                    While universal2 wheels can be built on x86_64, the arm64 part
                                    of the wheel cannot be tested on x86_64. Consider building
                                    universal2 wheels on an arm64 runner, if your CI provider offers
                                    this. Notably, an arm64 runner can also test the x86_64 part of
                                    the wheel, through Rosetta emulation. To silence this warning,
                                    set `CIBW_TEST_SKIP: "*-macosx_universal2:arm64"`.
                                    """
                                )
                            )
                        else:
                            msg = "unreachable"
                            raise RuntimeError(msg)

                        # skip this test
                        continue

                    is_cp38 = config.identifier.startswith("cp38-")
                    if testing_arch == "arm64" and is_cp38 and python_arch != "arm64":
                        log.warning(
                            unwrap(
                                """
                                While cibuildwheel can build CPython 3.8 universal2/arm64 wheels, we
                                cannot test the arm64 part of them, even when running on an Apple
                                Silicon machine. This is because we use the x86_64 installer of
                                CPython 3.8. See the discussion in
                                https://github.com/pypa/cibuildwheel/pull/1169 for the details. To
                                silence this warning, set `CIBW_TEST_SKIP: "cp38-macosx_*:arm64"`.
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

                    arch_prefix = []
                    uv_arch_args = []
                    if testing_arch != machine_arch:
                        if machine_arch == "arm64" and testing_arch == "x86_64":
                            # rosetta2 will provide the emulation with just the arch prefix.
                            arch_prefix = ["arch", "-x86_64"]
                            uv_arch_args = ["--python-platform", "x86_64-apple-darwin"]
                        else:
                            msg = f"don't know how to emulate {testing_arch} on {machine_arch}"
                            raise RuntimeError(msg)

                    # define a custom 'call' function that adds the arch prefix each time
                    call_with_arch = functools.partial(call, *arch_prefix)
                    shell_with_arch = functools.partial(call, *arch_prefix, "/bin/sh", "-c")

                    # set up a virtual environment to install and test from, to make sure
                    # there are no dependencies that were pulled in at build time.
                    venv_dir = identifier_tmp_dir / f"venv-test-{testing_arch}"
                    virtualenv_env = virtualenv(
                        config.version,
                        base_python,
                        venv_dir,
                        None,
                        use_uv=use_uv,
                        env=env,
                        pip_version=pip_version,
                    )
                    if use_uv:
                        pip_install = functools.partial(call, *pip, "install", *uv_arch_args)
                    else:
                        pip_install = functools.partial(call_with_arch, *pip, "install")

                    virtualenv_env["MACOSX_DEPLOYMENT_TARGET"] = get_test_macosx_deployment_target()

                    virtualenv_env = build_options.test_environment.as_dictionary(
                        prev_environment=virtualenv_env
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
                    if is_cp38 and python_arch == "x86_64":
                        virtualenv_env_install_wheel = virtualenv_env.copy()
                        virtualenv_env_install_wheel["SYSTEM_VERSION_COMPAT"] = "0"
                        log.notice(
                            unwrap(
                                """
                                Setting SYSTEM_VERSION_COMPAT=0 to ensure CPython 3.8 can get
                                correct macOS version and allow installation of wheels with
                                MACOSX_DEPLOYMENT_TARGET >= 11.0.
                                See https://github.com/pypa/cibuildwheel/issues/1767 for the
                                details.
                                """
                            )
                        )
                    else:
                        virtualenv_env_install_wheel = virtualenv_env

                    pip_install(
                        f"{repaired_wheel}{build_options.test_extras}",
                        env=virtualenv_env_install_wheel,
                    )

                    # test the wheel
                    if build_options.test_requires:
                        pip_install(
                            *build_options.test_requires,
                            env=virtualenv_env_install_wheel,
                        )

                    # run the tests from a temp dir, with an absolute path in the command
                    # (this ensures that Python runs the tests against the installed wheel
                    # and not the repo code)
                    test_command_prepared = prepare_command(
                        build_options.test_command,
                        project=Path.cwd(),
                        package=build_options.package_dir.resolve(),
                        wheel=repaired_wheel,
                    )

                    test_cwd = identifier_tmp_dir / "test_cwd"

                    if build_options.test_sources:
                        # only create test_cwd if it doesn't already exist - it
                        # may have been created during a previous `testing_arch`
                        if not test_cwd.exists():
                            test_cwd.mkdir()
                            copy_test_sources(
                                build_options.test_sources,
                                Path.cwd(),
                                test_cwd,
                            )
                    else:
                        # Use the test_fail.py file to raise a nice error if the user
                        # tries to run tests in the cwd
                        test_cwd.mkdir(exist_ok=True)
                        (test_cwd / "test_fail.py").write_text(
                            resources.TEST_FAIL_CWD_FILE.read_text()
                        )

                    shell_with_arch(test_command_prepared, cwd=test_cwd, env=virtualenv_env)

            # we're all done here; move it to output (overwrite existing)
            if compatible_wheel is None:
                output_wheel = build_options.output_dir.joinpath(repaired_wheel.name)
                moved_wheel = move_file(repaired_wheel, output_wheel)
                if moved_wheel != output_wheel.resolve():
                    log.warning(
                        f"{repaired_wheel} was moved to {moved_wheel} instead of {output_wheel}"
                    )
                built_wheels.append(output_wheel)

            # clean up
            shutil.rmtree(identifier_tmp_dir)

            log.build_end()
    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
