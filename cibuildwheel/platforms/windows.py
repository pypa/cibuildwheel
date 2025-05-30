import dataclasses
import json
import os
import platform as platform_module
import shutil
import subprocess
import textwrap
from collections.abc import MutableMapping, Set
from functools import cache
from pathlib import Path
from typing import assert_never

from filelock import FileLock

from .. import errors
from ..architecture import Architecture
from ..environment import ParsedEnvironment
from ..frontend import BuildFrontendConfig, BuildFrontendName, get_build_frontend_extra_flags
from ..logger import log
from ..options import Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import CIBW_CACHE_PATH, copy_test_sources, download, extract_zip, move_file
from ..util.helpers import prepare_command, unwrap
from ..util.packaging import combine_constraints, find_compatible_wheel, get_pip_version
from ..venv import constraint_flags, find_uv, virtualenv


def get_nuget_args(
    version: str, arch: str, free_threaded: bool, output_directory: Path
) -> list[str]:
    package_name = {
        "32": "pythonx86",
        "64": "python",
        "ARM64": "pythonarm64",
        # Aliases for platform.machine() return values
        "x86": "pythonx86",
        "AMD64": "python",
    }[arch]
    if free_threaded:
        package_name = f"{package_name}-freethreaded"
    return [
        package_name,
        "-Version",
        version,
        "-FallbackSource",
        "https://api.nuget.org/v3/index.json",
        "-OutputDirectory",
        str(output_directory),
    ]


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    arch: str
    identifier: str
    url: str | None = None


def all_python_configurations() -> list[PythonConfiguration]:
    config_dicts = resources.read_python_configs("windows")
    return [PythonConfiguration(**item) for item in config_dicts]


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],
) -> list[PythonConfiguration]:
    python_configurations = all_python_configurations()

    map_arch = {"32": Architecture.x86, "64": Architecture.AMD64, "ARM64": Architecture.ARM64}

    # skip builds as required
    python_configurations = [
        c
        for c in python_configurations
        if build_selector(c.identifier) and map_arch[c.arch] in architectures
    ]

    return python_configurations


@cache
def _ensure_nuget() -> Path:
    nuget = CIBW_CACHE_PATH / "nuget.exe"
    with FileLock(str(nuget) + ".lock"):
        if not nuget.exists():
            download("https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", nuget)
    return nuget


def install_cpython(configuration: PythonConfiguration, arch: str | None = None) -> Path:
    version = configuration.version
    free_threaded = "t-" in configuration.identifier
    if arch is None:
        arch = configuration.arch
    base_output_dir = CIBW_CACHE_PATH / "nuget-cpython"
    nuget_args = get_nuget_args(version, arch, free_threaded, base_output_dir)
    installation_path = base_output_dir / (nuget_args[0] + "." + version) / "tools"
    free_threaded_str = "-freethreaded" if free_threaded else ""
    with FileLock(str(base_output_dir) + f"-{version}{free_threaded_str}-{arch}.lock"):
        if not installation_path.exists():
            nuget = _ensure_nuget()
            call(nuget, "install", *nuget_args)
    return installation_path / "python.exe"


def install_pypy(tmp: Path, arch: str, url: str) -> Path:
    assert arch == "64"
    assert "win64" in url
    # Inside the PyPy zip file is a directory with the same name
    zip_filename = url.rsplit("/", 1)[-1]
    extension = ".zip"
    assert zip_filename.endswith(extension)
    installation_path = CIBW_CACHE_PATH / zip_filename[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            pypy_zip = tmp / zip_filename
            download(url, pypy_zip)
            # Extract to the parent directory because the zip file still contains a directory
            extract_zip(pypy_zip, installation_path.parent)
    return installation_path / "python.exe"


def install_graalpy(tmp: Path, url: str) -> Path:
    zip_filename = url.rsplit("/", 1)[-1]
    extension = ".zip"
    assert zip_filename.endswith(extension)
    installation_path = CIBW_CACHE_PATH / zip_filename[: -len(extension)]
    with FileLock(str(installation_path) + ".lock"):
        if not installation_path.exists():
            graalpy_zip = tmp / zip_filename
            download(url, graalpy_zip)
            # Extract to the parent directory because the zip file still contains a directory
            extract_zip(graalpy_zip, installation_path.parent)
    return installation_path / "bin" / "graalpy.exe"


def setup_setuptools_cross_compile(
    tmp: Path,
    python_configuration: PythonConfiguration,
    python_libs_base: Path,
    env: MutableMapping[str, str],
) -> None:
    distutils_cfg = tmp / "extra-setup.cfg"
    env["DIST_EXTRA_CONFIG"] = str(distutils_cfg)
    log.notice(f"Setting DIST_EXTRA_CONFIG={distutils_cfg} for cross-compilation")

    # Ensure our additional import libraries are made available, and explicitly
    # set the platform name
    map_plat = {"32": "win32", "64": "win-amd64", "ARM64": "win-arm64"}
    plat_name = map_plat[python_configuration.arch]

    # Set environment variable so that setuptools._distutils.get_platform()
    # identifies the target, not the host
    vscmd_arg_tgt_arch = {"32": "x86", "64": "x64", "ARM64": "arm64"}
    current_tgt_arch = vscmd_arg_tgt_arch[python_configuration.arch]
    if (env.get("VSCMD_ARG_TGT_ARCH") or current_tgt_arch) != current_tgt_arch:
        msg = f"VSCMD_ARG_TGT_ARCH must be set to {current_tgt_arch!r}, got {env['VSCMD_ARG_TGT_ARCH']!r}. If you're setting up MSVC yourself (e.g. using vcvarsall.bat or msvc-dev-cmd), make sure to target the right architecture. Alternatively, run cibuildwheel without configuring MSVC, and let the build backend handle it."
        raise errors.FatalError(msg)
    env["VSCMD_ARG_TGT_ARCH"] = current_tgt_arch

    # (This file must be default/locale encoding, so we can't pass 'encoding')
    distutils_cfg.write_text(
        textwrap.dedent(
            f"""\
            [build]
            plat_name={plat_name}
            [build_ext]
            library_dirs={python_libs_base}
            plat_name={plat_name}
            [bdist_wheel]
            plat_name={plat_name}
            """
        )
    )

    # setuptools builds require explicit override of PYD extension
    # This is because it always gets the extension from the running
    # interpreter, and has no logic to construct it. Currently, CPython's
    # extensions follow our identifiers, but if they ever diverge in the
    # future, we will need to store new data
    log.notice(
        f"Setting SETUPTOOLS_EXT_SUFFIX=.{python_configuration.identifier}.pyd for cross-compilation"
    )
    env["SETUPTOOLS_EXT_SUFFIX"] = f".{python_configuration.identifier}.pyd"

    # Cross-compilation requires fixes that only exist in setuptools's copy of
    # distutils, so ensure that it is activated
    # Since not all projects can handle the newer distutils, display a warning
    # to help them figure out what may have gone wrong if this breaks for them
    log.notice("Setting SETUPTOOLS_USE_DISTUTILS=local as it is required for cross-compilation")
    env["SETUPTOOLS_USE_DISTUTILS"] = "local"


# These cross-compile setup functions have the same signature by design
def setup_rust_cross_compile(
    tmp: Path,  # noqa: ARG001
    python_configuration: PythonConfiguration,
    python_libs_base: Path,  # noqa: ARG001
    env: MutableMapping[str, str],
) -> None:
    # Assume that MSVC will be used, because we already know that we are
    # cross-compiling. MinGW users can set CARGO_BUILD_TARGET themselves
    # and we will respect the existing value.
    cargo_target = {
        "64": "x86_64-pc-windows-msvc",
        "32": "i686-pc-windows-msvc",
        "ARM64": "aarch64-pc-windows-msvc",
    }.get(python_configuration.arch)

    # CARGO_BUILD_TARGET is the variable used by Cargo and setuptools_rust
    if env.get("CARGO_BUILD_TARGET"):
        if env["CARGO_BUILD_TARGET"] != cargo_target:
            log.notice("Not overriding CARGO_BUILD_TARGET as it has already been set")
        # No message if it was set to what we were planning to set it to
    elif cargo_target:
        log.notice(f"Setting CARGO_BUILD_TARGET={cargo_target} for cross-compilation")
        env["CARGO_BUILD_TARGET"] = cargo_target
    else:
        log.warning(
            f"Unable to configure Rust cross-compilation for architecture {python_configuration.arch}"
        )


def can_use_uv(python_configuration: PythonConfiguration) -> bool:
    conditions = (not python_configuration.identifier.startswith("pp38-"),)
    return all(conditions)


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    dependency_constraint: Path | None,
    environment: ParsedEnvironment,
    build_frontend: BuildFrontendName,
) -> tuple[Path, dict[str, str]]:
    tmp.mkdir()
    implementation_id = python_configuration.identifier.split("-")[0]
    python_libs_base = None
    log.step(f"Installing Python {implementation_id}...")
    if implementation_id.startswith("cp"):
        native_arch = platform_module.machine()
        base_python = install_cpython(python_configuration)
        if python_configuration.arch == "ARM64" != native_arch:
            # To cross-compile for ARM64, we need a native CPython to run the
            # build, and a copy of the ARM64 import libraries ('.\libs\*.lib')
            # for any extension modules.
            python_libs_base = base_python.parent / "libs"
            log.step(f"Installing native Python {native_arch} for cross-compilation...")
            base_python = install_cpython(python_configuration, arch=native_arch)
    elif implementation_id.startswith("pp"):
        assert python_configuration.url is not None
        base_python = install_pypy(tmp, python_configuration.arch, python_configuration.url)
    elif implementation_id.startswith("gp"):
        base_python = install_graalpy(tmp, python_configuration.url or "")
    else:
        msg = "Unknown Python implementation"
        raise ValueError(msg)
    assert base_python.exists()

    if build_frontend == "build[uv]" and not can_use_uv(python_configuration):
        build_frontend = "build"

    use_uv = build_frontend == "build[uv]"
    uv_path = find_uv()

    log.step("Setting up build environment...")
    venv_path = tmp / "venv"
    env = virtualenv(
        python_configuration.version,
        base_python,
        venv_path,
        dependency_constraint,
        use_uv=use_uv,
    )

    # set up environment variables for run_with_env
    env["PYTHON_VERSION"] = python_configuration.version
    env["PYTHON_ARCH"] = python_configuration.arch
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    # update env with results from CIBW_ENVIRONMENT
    env = environment.as_dictionary(prev_environment=env)

    # check what Python version we're on
    where_python = call("where", "python", env=env, capture_stdout=True).splitlines()[0].strip()
    print(where_python)
    if where_python != str(venv_path / "Scripts" / "python.exe"):
        msg = "python available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it."
        raise errors.FatalError(msg)
    call("python", "--version", env=env)
    call("python", "-c", "\"import struct; print(struct.calcsize('P') * 8)\"", env=env)

    # check what pip version we're on
    if not use_uv:
        assert (venv_path / "Scripts" / "pip.exe").exists()
        where_pip = call("where", "pip", env=env, capture_stdout=True).splitlines()[0].strip()
        print(where_pip)
        if where_pip.strip() != str(venv_path / "Scripts" / "pip.exe"):
            msg = "pip available on PATH doesn't match our installed instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it."
            raise errors.FatalError(msg)
        call("pip", "--version", env=env)

    log.step("Installing build tools...")
    if build_frontend == "build":
        call(
            "pip",
            "install",
            "--upgrade",
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
            "build[virtualenv]",
            *constraint_flags(dependency_constraint),
            env=env,
        )

    if python_libs_base:
        # Set up the environment for various backends to enable cross-compilation
        setup_setuptools_cross_compile(tmp, python_configuration, python_libs_base, env)
        setup_rust_cross_compile(tmp, python_configuration, python_libs_base, env)

    if implementation_id.startswith("gp"):
        # GraalPy fails to discover compilers, setup the relevant environment
        # variables. Adapted from
        # https://github.com/microsoft/vswhere/wiki/Start-Developer-Command-Prompt
        # Remove when https://github.com/oracle/graalpython/issues/492 is fixed.
        vcpath = call(
            Path(os.environ["PROGRAMFILES(X86)"])
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe",
            "-products",
            "*",
            "-latest",
            "-property",
            "installationPath",
            capture_stdout=True,
        ).strip()
        log.notice(f"Discovering Visual Studio for GraalPy at {vcpath}")
        vcvars_file = tmp / "vcvars.json"
        call(
            f"{vcpath}\\Common7\\Tools\\vsdevcmd.bat",
            "-no_logo",
            "-arch=amd64",
            "-host_arch=amd64",
            "&&",
            "python",
            "-c",
            # this command needs to be one line for Windows reasons
            "import sys, json, pathlib, os; pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(os.environ)))",
            vcvars_file,
            env=env,
        )
        with open(vcvars_file, encoding="utf-8") as f:
            vcvars = json.load(f)
        env.update(vcvars)

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
            before_all_prepared = prepare_command(
                before_all_options.before_all, project=".", package=options.globals.package_dir
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            build_frontend = build_options.build_frontend or BuildFrontendConfig("build")

            use_uv = build_frontend.name == "build[uv]" and can_use_uv(config)
            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier
            identifier_tmp_dir.mkdir()
            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"

            constraints_path = build_options.dependency_constraints.get_for_python_version(
                version=config.version,
                tmp_dir=identifier_tmp_dir,
            )

            # install Python
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
                # run the before_build command
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build,
                        project=".",
                        package=options.globals.package_dir,
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")
                built_wheel_dir.mkdir()

                extra_flags = get_build_frontend_extra_flags(
                    build_frontend, build_options.build_verbosity, build_options.config_settings
                )

                if (
                    config.identifier.startswith("gp")
                    and build_frontend.name == "build"
                    and "--no-isolation" not in extra_flags
                    and "-n" not in extra_flags
                ):
                    # GraalPy fails to discover its standard library when a venv is created
                    # from a virtualenv seeded executable. See
                    # https://github.com/oracle/graalpython/issues/491 and remove this once
                    # fixed upstream.
                    log.notice(
                        "Disabling build isolation to workaround GraalPy bug. If the build fails, consider using pip or build[uv] as build frontend."
                    )
                    shell("graalpy -m pip install setuptools wheel", env=env)
                    extra_flags = [*extra_flags, "-n"]

                build_env = env.copy()
                if pip_version is not None:
                    build_env["VIRTUALENV_PIP"] = pip_version

                if constraints_path:
                    combine_constraints(build_env, constraints_path, identifier_tmp_dir)

                if build_frontend.name == "pip":
                    # Path.resolve() is needed. Without it pip wheel may try to fetch package from pypi.org
                    # see https://github.com/pypa/cibuildwheel/pull/369
                    call(
                        "python",
                        "-m",
                        "pip",
                        "wheel",
                        options.globals.package_dir.resolve(),
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

                # repair the wheel
                repaired_wheel_dir.mkdir()

                if built_wheel.name.endswith("none-any.whl"):
                    raise errors.NonPlatformWheelError()

                if build_options.repair_command:
                    log.step("Repairing wheel...")
                    repair_command_prepared = prepare_command(
                        build_options.repair_command,
                        wheel=built_wheel,
                        dest_dir=repaired_wheel_dir,
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

            test_selected = options.globals.test_selector(config.identifier)
            if test_selected and config.arch == "ARM64" != platform_module.machine():
                log.warning(
                    unwrap(
                        """
                            While arm64 wheels can be built on other platforms, they cannot
                            be tested. An arm64 runner is required. To silence this warning,
                            set `CIBW_TEST_SKIP: "*-win_arm64"`.
                            """
                    )
                )
                # skip this test
            elif test_selected and build_options.test_command:
                log.step("Testing wheel...")
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.
                venv_dir = identifier_tmp_dir / "venv-test"
                virtualenv_env = virtualenv(
                    config.version,
                    base_python,
                    venv_dir,
                    None,
                    use_uv=use_uv,
                    env=env,
                    pip_version=pip_version,
                )

                virtualenv_env = build_options.test_environment.as_dictionary(
                    prev_environment=virtualenv_env
                )

                # check that we are using the Python from the virtual environment
                call("where", "python", env=virtualenv_env)

                if build_options.before_test:
                    before_test_prepared = prepare_command(
                        build_options.before_test,
                        project=".",
                        package=build_options.package_dir,
                    )
                    shell(before_test_prepared, env=virtualenv_env)

                pip = ["uv", "pip"] if use_uv else ["pip"]

                # install the wheel
                call(
                    *pip,
                    "install",
                    str(repaired_wheel) + build_options.test_extras,
                    env=virtualenv_env,
                )

                # test the wheel
                if build_options.test_requires:
                    call(*pip, "install", *build_options.test_requires, env=virtualenv_env)

                # run the tests from a temp dir, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_cwd = identifier_tmp_dir / "test_cwd"
                test_cwd.mkdir()

                if build_options.test_sources:
                    copy_test_sources(
                        build_options.test_sources,
                        Path.cwd(),
                        test_cwd,
                    )
                else:
                    # Use the test_fail.py file to raise a nice error if the user
                    # tries to run tests in the cwd
                    (test_cwd / "test_fail.py").write_text(resources.TEST_FAIL_CWD_FILE.read_text())

                test_command_prepared = prepare_command(
                    build_options.test_command,
                    project=Path.cwd(),
                    package=options.globals.package_dir.resolve(),
                    wheel=repaired_wheel,
                )
                shell(test_command_prepared, cwd=test_cwd, env=virtualenv_env)

            # we're all done here; move it to output (remove if already exists)
            if compatible_wheel is None:
                output_wheel = build_options.output_dir.joinpath(repaired_wheel.name)
                moved_wheel = move_file(repaired_wheel, output_wheel)
                if moved_wheel != output_wheel.resolve():
                    log.warning(
                        f"{repaired_wheel} was moved to {moved_wheel} instead of {output_wheel}"
                    )
                built_wheels.append(output_wheel)

            # clean up
            # (we ignore errors because occasionally Windows fails to unlink a file and we
            # don't want to abort a build because of that)
            shutil.rmtree(identifier_tmp_dir, ignore_errors=True)

            log.build_end()
    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
