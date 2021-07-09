import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Set, Tuple, cast

from .architecture import Architecture
from .environment import ParsedEnvironment
from .logger import log
from .typing import Literal, PathOrStr, assert_never
from .util import (
    BuildFrontend,
    BuildOptions,
    BuildSelector,
    NonPlatformWheelError,
    download,
    get_build_verbosity_extra_flags,
    get_pip_version,
    install_certifi_script,
    prepare_command,
    read_python_configs,
    unwrap,
)


def call(
    args: Sequence[PathOrStr],
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    shell: bool = False,
) -> None:
    # print the command executing for the logs
    if shell:
        print(f"+ {args}")
    else:
        print("+ " + " ".join(shlex.quote(str(a)) for a in args))

    subprocess.run(args, env=env, cwd=cwd, shell=shell, check=True)


def get_macos_version() -> Tuple[int, int]:
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


def get_macos_sdks() -> List[str]:
    output = subprocess.run(
        ["xcodebuild", "-showsdks"],
        universal_newlines=True,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout

    return [m.group(1) for m in re.finditer(r"-sdk (macosx\S+)", output)]


class PythonConfiguration(NamedTuple):
    version: str
    identifier: str
    url: str


def get_python_configurations(
    build_selector: BuildSelector, architectures: Set[Architecture]
) -> List[PythonConfiguration]:

    full_python_configs = read_python_configs("macos")

    python_configurations = [PythonConfiguration(**item) for item in full_python_configs]

    # filter out configs that don't match any of the selected architectures
    python_configurations = [
        c
        for c in python_configurations
        if any(c.identifier.endswith(a.value) for a in architectures)
    ]

    # skip builds as required by BUILD/SKIP
    python_configurations = [c for c in python_configurations if build_selector(c.identifier)]

    # When running on macOS 11 and x86_64, the reported OS is '10.16', but
    # there is no such OS - it really means macOS 11.
    if get_macos_version() >= (10, 16):
        if any(c.identifier.startswith("pp") for c in python_configurations):
            # pypy doesn't work on macOS 11 yet
            # See https://foss.heptapod.net/pypy/pypy/-/issues/3314
            log.warning(
                unwrap(
                    """
                    PyPy is currently unsupported when building on macOS 11. To build macOS PyPy
                    wheels, build on an older OS, such as macOS 10.15. To silence this warning,
                    deselect PyPy by adding "pp*-macosx*" to your CIBW_SKIP option.
                    """
                )
            )
            python_configurations = [
                c for c in python_configurations if not c.identifier.startswith("pp")
            ]

    return python_configurations


SYMLINKS_DIR = Path("/tmp/cibw_bin")


def make_symlinks(installation_bin_path: Path, python_executable: str, pip_executable: str) -> None:
    assert (installation_bin_path / python_executable).exists()

    # Python bin folders on Mac don't symlink `python3` to `python`, and neither
    # does PyPy for `pypy` or `pypy3`, so we do that so `python` and `pip` always
    # point to the active configuration.
    if SYMLINKS_DIR.exists():
        shutil.rmtree(SYMLINKS_DIR)
    SYMLINKS_DIR.mkdir(parents=True)

    (SYMLINKS_DIR / "python").symlink_to(installation_bin_path / python_executable)
    (SYMLINKS_DIR / "python-config").symlink_to(
        installation_bin_path / (python_executable + "-config")
    )
    (SYMLINKS_DIR / "pip").symlink_to(installation_bin_path / pip_executable)


def install_cpython(version: str, url: str) -> Path:
    installed_system_packages = subprocess.run(
        ["pkgutil", "--pkgs"], universal_newlines=True, check=True, stdout=subprocess.PIPE
    ).stdout.splitlines()

    # if this version of python isn't installed, get it from python.org and install
    python_package_identifier = f"org.python.Python.PythonFramework-{version}"
    python_executable = "python3"
    installation_bin_path = Path(f"/Library/Frameworks/Python.framework/Versions/{version}/bin")

    if python_package_identifier not in installed_system_packages:
        # download the pkg
        download(url, Path("/tmp/Python.pkg"))
        # install
        call(["sudo", "installer", "-pkg", "/tmp/Python.pkg", "-target", "/"])
        call(["sudo", str(installation_bin_path / python_executable), str(install_certifi_script)])

    pip_executable = "pip3"
    make_symlinks(installation_bin_path, python_executable, pip_executable)

    return installation_bin_path


def install_pypy(version: str, url: str) -> Path:
    pypy_tar_bz2 = url.rsplit("/", 1)[-1]
    extension = ".tar.bz2"
    assert pypy_tar_bz2.endswith(extension)
    pypy_base_filename = pypy_tar_bz2[: -len(extension)]
    installation_path = Path("/tmp") / pypy_base_filename
    if not installation_path.exists():
        downloaded_tar_bz2 = Path("/tmp") / pypy_tar_bz2
        download(url, downloaded_tar_bz2)
        call(["tar", "-C", "/tmp", "-xf", downloaded_tar_bz2])

    installation_bin_path = installation_path / "bin"
    python_executable = "pypy3"
    pip_executable = "pip3"
    make_symlinks(installation_bin_path, python_executable, pip_executable)

    return installation_bin_path


def setup_python(
    python_configuration: PythonConfiguration,
    dependency_constraint_flags: Sequence[PathOrStr],
    environment: ParsedEnvironment,
    build_frontend: BuildFrontend,
) -> Dict[str, str]:

    implementation_id = python_configuration.identifier.split("-")[0]
    log.step(f"Installing Python {implementation_id}...")

    if implementation_id.startswith("cp"):
        installation_bin_path = install_cpython(
            python_configuration.version, python_configuration.url
        )
    elif implementation_id.startswith("pp"):
        installation_bin_path = install_pypy(python_configuration.version, python_configuration.url)
    else:
        raise ValueError("Unknown Python implementation")

    log.step("Setting up build environment...")

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        [
            str(SYMLINKS_DIR),
            str(installation_bin_path),
            env["PATH"],
        ]
    )

    # Fix issue with site.py setting the wrong `sys.prefix`, `sys.exec_prefix`,
    # `sys.path`, ... for PyPy: https://foss.heptapod.net/pypy/pypy/issues/3175
    # Also fix an issue with the shebang of installed scripts inside the
    # testing virtualenv- see https://github.com/theacodes/nox/issues/44 and
    # https://github.com/pypa/virtualenv/issues/620
    # Also see https://github.com/python/cpython/pull/9516
    env.pop("__PYVENV_LAUNCHER__", None)
    env = environment.as_dictionary(prev_environment=env)

    # we version pip ourselves, so we don't care about pip version checking
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # check what version we're on
    call(["which", "python"], env=env)
    call(["python", "--version"], env=env)
    which_python = subprocess.run(
        ["which", "python"], env=env, universal_newlines=True, check=True, stdout=subprocess.PIPE
    ).stdout.strip()
    if which_python != "/tmp/cibw_bin/python":
        print(
            "cibuildwheel: python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Install pip

    requires_reinstall = not (installation_bin_path / "pip").exists()
    if requires_reinstall:
        # maybe pip isn't installed at all. ensurepip resolves that.
        call(["python", "-m", "ensurepip"], env=env, cwd="/tmp")

    # upgrade pip to the version matching our constraints
    # if necessary, reinstall it to ensure that it's available on PATH as 'pip'
    call(
        [
            "python",
            "-m",
            "pip",
            "install",
            "--force-reinstall" if requires_reinstall else "--upgrade",
            "pip",
            *dependency_constraint_flags,
        ],
        env=env,
        cwd="/tmp",
    )

    assert (installation_bin_path / "pip").exists()
    call(["which", "pip"], env=env)
    call(["pip", "--version"], env=env)
    which_pip = subprocess.run(
        ["which", "pip"], env=env, universal_newlines=True, check=True, stdout=subprocess.PIPE
    ).stdout.strip()
    if which_pip != "/tmp/cibw_bin/pip":
        print(
            "cibuildwheel: pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it.",
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
            [
                "pip",
                "install",
                "--upgrade",
                "setuptools",
                "wheel",
                "delocate",
                *dependency_constraint_flags,
            ],
            env=env,
        )
    elif build_frontend == "build":
        call(
            [
                "pip",
                "install",
                "--upgrade",
                "delocate",
                "build[virtualenv]",
                *dependency_constraint_flags,
            ],
            env=env,
        )
    else:
        assert_never(build_frontend)

    return env


def build(options: BuildOptions) -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="cibuildwheel"))
    built_wheel_dir = temp_dir / "built_wheel"
    repaired_wheel_dir = temp_dir / "repaired_wheel"

    try:
        if options.before_all:
            log.step("Running before_all...")
            env = options.environment.as_dictionary(prev_environment=os.environ)
            env.setdefault("MACOSX_DEPLOYMENT_TARGET", "10.9")
            before_all_prepared = prepare_command(
                options.before_all, project=".", package=options.package_dir
            )
            call([before_all_prepared], shell=True, env=env)

        python_configurations = get_python_configurations(
            options.build_selector, options.architectures
        )

        for config in python_configurations:
            log.build_start(config.identifier)

            config_is_arm64 = config.identifier.endswith("arm64")
            config_is_universal2 = config.identifier.endswith("universal2")

            dependency_constraint_flags: Sequence[PathOrStr] = []
            if options.dependency_constraints:
                dependency_constraint_flags = [
                    "-c",
                    options.dependency_constraints.get_for_python_version(config.version),
                ]

            env = setup_python(
                config,
                dependency_constraint_flags,
                options.environment,
                options.build_frontend,
            )

            if options.before_build:
                log.step("Running before_build...")
                before_build_prepared = prepare_command(
                    options.before_build, project=".", package=options.package_dir
                )
                call(before_build_prepared, env=env, shell=True)

            log.step("Building wheel...")
            if built_wheel_dir.exists():
                shutil.rmtree(built_wheel_dir)
            built_wheel_dir.mkdir(parents=True)

            verbosity_flags = get_build_verbosity_extra_flags(options.build_verbosity)

            if options.build_frontend == "pip":
                # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                # see https://github.com/pypa/cibuildwheel/pull/369
                call(
                    [
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        options.package_dir.resolve(),
                        f"--wheel-dir={built_wheel_dir}",
                        "--no-deps",
                        *verbosity_flags,
                    ],
                    env=env,
                )
            elif options.build_frontend == "build":
                config_setting = " ".join(verbosity_flags)
                build_env = env.copy()
                if options.dependency_constraints:
                    constr = options.dependency_constraints.get_for_python_version(config.version)
                    build_env["PIP_CONSTRAINT"] = constr.as_uri()
                build_env["VIRTUALENV_PIP"] = get_pip_version(env)
                call(
                    [
                        "python",
                        "-m",
                        "build",
                        options.package_dir,
                        "--wheel",
                        f"--outdir={built_wheel_dir}",
                        f"--config-setting={config_setting}",
                    ],
                    env=build_env,
                )
            else:
                assert_never(options.build_frontend)

            built_wheel = next(built_wheel_dir.glob("*.whl"))

            if repaired_wheel_dir.exists():
                shutil.rmtree(repaired_wheel_dir)
            repaired_wheel_dir.mkdir(parents=True)

            if built_wheel.name.endswith("none-any.whl"):
                raise NonPlatformWheelError()

            if options.repair_command:
                log.step("Repairing wheel...")

                if config_is_universal2:
                    delocate_archs = "x86_64,arm64"
                elif config_is_arm64:
                    delocate_archs = "arm64"
                else:
                    delocate_archs = "x86_64"

                repair_command_prepared = prepare_command(
                    options.repair_command,
                    wheel=built_wheel,
                    dest_dir=repaired_wheel_dir,
                    delocate_archs=delocate_archs,
                )
                call(repair_command_prepared, env=env, shell=True)
            else:
                shutil.move(str(built_wheel), repaired_wheel_dir)

            repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

            log.step_end()

            if options.test_command and options.test_selector(config.identifier):
                machine_arch = platform.machine()
                testing_archs: List[Literal["x86_64", "arm64"]] = []

                if config_is_arm64:
                    testing_archs = ["arm64"]
                elif config_is_universal2:
                    testing_archs = ["x86_64", "arm64"]
                else:
                    testing_archs = ["x86_64"]

                for testing_arch in testing_archs:
                    if config_is_universal2:
                        arch_specific_identifier = f"{config.identifier}:{testing_arch}"
                        if not options.test_selector(arch_specific_identifier):
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
                            raise RuntimeError("unreachable")

                        # skip this test
                        continue

                    log.step(
                        "Testing wheel..."
                        if testing_arch == machine_arch
                        else f"Testing wheel on {testing_arch}..."
                    )

                    # set up a virtual environment to install and test from, to make sure
                    # there are no dependencies that were pulled in at build time.
                    call(["pip", "install", "virtualenv", *dependency_constraint_flags], env=env)
                    venv_dir = Path(tempfile.mkdtemp())

                    arch_prefix = []
                    if testing_arch != machine_arch:
                        if machine_arch == "arm64" and testing_arch == "x86_64":
                            # rosetta2 will provide the emulation with just the arch prefix.
                            arch_prefix = ["arch", "-x86_64"]
                        else:
                            raise RuntimeError(
                                "don't know how to emulate {testing_arch} on {machine_arch}"
                            )

                    # define a custom 'call' function that adds the arch prefix each time
                    def call_with_arch(args: Sequence[PathOrStr], **kwargs: Any) -> None:
                        if isinstance(args, str):
                            args = " ".join(arch_prefix) + " " + args
                        else:
                            args = [*arch_prefix, *args]
                        call(args, **kwargs)

                    # Use --no-download to ensure determinism by using seed libraries
                    # built into virtualenv
                    call_with_arch(
                        ["python", "-m", "virtualenv", "--no-download", venv_dir], env=env
                    )

                    virtualenv_env = env.copy()
                    virtualenv_env["PATH"] = os.pathsep.join(
                        [
                            str(venv_dir / "bin"),
                            virtualenv_env["PATH"],
                        ]
                    )

                    # check that we are using the Python from the virtual environment
                    call_with_arch(["which", "python"], env=virtualenv_env)

                    if options.before_test:
                        before_test_prepared = prepare_command(
                            options.before_test, project=".", package=options.package_dir
                        )
                        call_with_arch(before_test_prepared, env=virtualenv_env, shell=True)

                    # install the wheel
                    call_with_arch(
                        ["pip", "install", f"{repaired_wheel}{options.test_extras}"],
                        env=virtualenv_env,
                    )

                    # test the wheel
                    if options.test_requires:
                        call_with_arch(
                            ["pip", "install"] + options.test_requires, env=virtualenv_env
                        )

                    # run the tests from $HOME, with an absolute path in the command
                    # (this ensures that Python runs the tests against the installed wheel
                    # and not the repo code)
                    test_command_prepared = prepare_command(
                        options.test_command,
                        project=Path(".").resolve(),
                        package=options.package_dir.resolve(),
                    )
                    call_with_arch(
                        test_command_prepared,
                        cwd=os.environ["HOME"],
                        env=virtualenv_env,
                        shell=True,
                    )

                    # clean up
                    shutil.rmtree(venv_dir)

            # we're all done here; move it to output (overwrite existing)
            shutil.move(str(repaired_wheel), options.output_dir)
            log.build_end()
    except subprocess.CalledProcessError as error:
        log.step_end_with_error(
            f"Command {error.cmd} failed with code {error.returncode}. {error.stdout}"
        )
        sys.exit(1)
