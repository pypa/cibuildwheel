import dataclasses
import functools
import json
import os
import shutil
import sys
import tomllib
import typing
from collections.abc import Set
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, TypedDict

from filelock import FileLock

from .. import errors
from ..architecture import Architecture
from ..environment import ParsedEnvironment
from ..frontend import BuildFrontendConfig, get_build_frontend_extra_flags
from ..logger import log
from ..options import Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import (
    CIBW_CACHE_PATH,
    copy_test_sources,
    download,
    extract_tar,
    extract_zip,
    move_file,
)
from ..util.helpers import prepare_command, unwrap, unwrap_preserving_paragraphs
from ..util.packaging import combine_constraints, find_compatible_wheel, get_pip_version
from ..util.python_build_standalone import (
    PythonBuildStandaloneError,
    create_python_build_standalone_environment,
)
from ..venv import constraint_flags, virtualenv

IS_WIN: Final[bool] = sys.platform.startswith("win")


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    identifier: str
    default_pyodide_version: str
    node_version: str


class PyodideXBuildEnvInfoVersionRange(TypedDict):
    min: str | None
    max: str | None


class PyodideXBuildEnvInfo(TypedDict):
    version: str
    python: str
    emscripten: str
    pyodide_build: PyodideXBuildEnvInfoVersionRange
    compatible: bool


@functools.cache
def ensure_node(major_version: str) -> Path:
    with resources.NODEJS.open("rb") as f:
        loaded_file = tomllib.load(f)
    version = str(loaded_file[major_version])
    base_url = str(loaded_file["url"])
    ext = "zip" if IS_WIN else "tar.xz"
    platform = "win" if IS_WIN else ("darwin" if sys.platform.startswith("darwin") else "linux")
    linux_arch = Architecture.native_arch("linux")
    assert linux_arch is not None
    arch = {"x86_64": "x64", "i686": "x86", "aarch64": "arm64"}.get(
        linux_arch.value, linux_arch.value
    )
    name = f"node-{version}-{platform}-{arch}"
    path = CIBW_CACHE_PATH / name
    with FileLock(str(path) + ".lock"):
        if not path.exists():
            url = f"{base_url}{version}/{name}.{ext}"
            with TemporaryDirectory() as tmp_path:
                archive = Path(tmp_path) / f"{name}.{ext}"
                download(url, archive)
                if ext == "zip":
                    extract_zip(archive, path.parent)
                else:
                    extract_tar(archive, path.parent)
    assert path.exists()
    if not IS_WIN:
        return path / "bin"
    return path


def install_emscripten(tmp: Path, version: str) -> Path:
    url = f"https://github.com/emscripten-core/emsdk/archive/refs/tags/{version}.zip"
    installation_path = CIBW_CACHE_PATH / f"emsdk-{version}"
    emsdk_path = installation_path / f"emsdk-{version}/emsdk"
    emcc_path = installation_path / f"emsdk-{version}/upstream/emscripten/emcc"
    with FileLock(f"{installation_path}.lock"):
        if installation_path.exists():
            return emcc_path
        emsdk_zip = tmp / "emsdk.zip"
        download(url, emsdk_zip)
        installation_path.mkdir()
        extract_zip(emsdk_zip, installation_path)
        call(emsdk_path, "install", version)
        call(emsdk_path, "activate", version)

    return emcc_path


def get_all_xbuildenv_version_info(env: dict[str, str]) -> list[PyodideXBuildEnvInfo]:
    xbuildenvs_info_str = call(
        "pyodide",
        "xbuildenv",
        "search",
        "--json",
        "--all",
        env=env,
        cwd=CIBW_CACHE_PATH,
        capture_stdout=True,
    ).strip()

    xbuildenvs_info = json.loads(xbuildenvs_info_str)

    if "environments" not in xbuildenvs_info:
        msg = f"Invalid xbuildenvs info, got {xbuildenvs_info}"
        raise ValueError(msg)

    return typing.cast(list[PyodideXBuildEnvInfo], xbuildenvs_info["environments"])


def get_xbuildenv_version_info(
    env: dict[str, str], version: str, pyodide_build_version: str
) -> PyodideXBuildEnvInfo:
    xbuildenvs_info = get_all_xbuildenv_version_info(env)
    for xbuildenv_info in xbuildenvs_info:
        if xbuildenv_info["version"] == version:
            return xbuildenv_info

    msg = unwrap(f"""
        Could not find Pyodide cross-build environment version {version} in the available
        versions as reported by pyodide-build v{pyodide_build_version}.
        Available pyodide xbuildenv versions are:
        {", ".join(e["version"] for e in xbuildenvs_info if e["compatible"])}
    """)
    raise errors.FatalError(msg)


# The default pyodide xbuildenv version that's specified in
# build-platforms.toml is compatible with the pyodide-build version that's
# pinned in the bundled constraints file. But if the user changes
# pyodide-version and/or dependency-constraints in the cibuildwheel config, we
# need to check if the xbuildenv version is compatible with the pyodide-build
# version.
def validate_pyodide_build_version(
    xbuildenv_info: PyodideXBuildEnvInfo, pyodide_build_version: str
) -> None:
    """
    Validate the Pyodide version is compatible with the installed
    pyodide-build version.
    """

    pyodide_version = xbuildenv_info["version"]

    if not xbuildenv_info["compatible"]:
        msg = unwrap_preserving_paragraphs(f"""
            The Pyodide xbuildenv version {pyodide_version} is not compatible
            with the pyodide-build version {pyodide_build_version}. Please use
            the 'pyodide xbuildenv search --all' command to find a compatible
            version.

            Set the pyodide-build version using the `dependency-constraints`
            option, or set the Pyodide xbuildenv version using the
            `pyodide-version` option.
        """)
        raise errors.FatalError(msg)


def install_xbuildenv(env: dict[str, str], pyodide_build_version: str, pyodide_version: str) -> str:
    """Install a particular Pyodide xbuildenv version and set a path to the Pyodide root."""
    # Since pyodide-build was unvendored from Pyodide v0.27.0, the versions of
    # pyodide-build are uncoupled from the versions of Pyodide. So, we specify
    # both the pyodide-build version and the Pyodide version in the temp path.
    xbuildenv_cache_path = CIBW_CACHE_PATH / f"pyodide-build-{pyodide_build_version}"
    pyodide_root = xbuildenv_cache_path / pyodide_version / "xbuildenv" / "pyodide-root"

    with FileLock(CIBW_CACHE_PATH / "xbuildenv.lock"):
        if pyodide_root.exists():
            return str(pyodide_root)

        # We don't want to mutate env but we need to delete any existing
        # PYODIDE_ROOT so copy it first.
        env = dict(env)
        env.pop("PYODIDE_ROOT", None)

        # Install the xbuildenv
        call(
            "pyodide",
            "xbuildenv",
            "install",
            "--path",
            str(xbuildenv_cache_path),
            pyodide_version,
            env=env,
            cwd=CIBW_CACHE_PATH,
        )
        assert pyodide_root.exists()

    return str(pyodide_root)


def get_base_python(tmp: Path, python_configuration: PythonConfiguration) -> Path:
    try:
        return create_python_build_standalone_environment(
            python_version=python_configuration.version,
            temp_dir=tmp,
            cache_dir=CIBW_CACHE_PATH,
        )
    except PythonBuildStandaloneError as e:
        msg = unwrap(f"""
            Failed to create a Python build environment:
            {e}
        """)
        raise errors.FatalError(msg) from e


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    constraints_path: Path | None,
    environment: ParsedEnvironment,
    user_pyodide_version: str | None,
) -> dict[str, str]:
    log.step("Installing a base python environment...")
    base_python = get_base_python(tmp / "base", python_configuration)

    log.step("Setting up build environment...")
    pyodide_version = user_pyodide_version or python_configuration.default_pyodide_version
    venv_path = tmp / "venv"
    env = virtualenv(python_configuration.version, base_python, venv_path, None, use_uv=False)
    venv_bin_path = venv_path / "bin"
    assert venv_bin_path.exists()
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
        *constraint_flags(constraints_path),
        env=env,
        cwd=venv_path,
    )

    env = environment.as_dictionary(prev_environment=env)

    # check what Python version we're on
    which_python = call("which", "python", env=env, capture_stdout=True).strip()
    print(which_python)
    if which_python != str(venv_bin_path / "python"):
        msg = "python available on PATH doesn't match our venv instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert python above it."
        raise errors.FatalError(msg)
    call("python", "--version", env=env)

    # check what pip version we're on
    assert (venv_bin_path / "pip").exists()
    which_pip = call("which", "pip", env=env, capture_stdout=True).strip()
    print(which_pip)
    if which_pip != str(venv_bin_path / "pip"):
        msg = "pip available on PATH doesn't match our venv instance. If you have modified PATH, ensure that you don't overwrite cibuildwheel's entry or insert pip above it."
        raise errors.FatalError(msg)
    call("pip", "--version", env=env)

    log.step("Installing build tools...")
    call(
        "pip",
        "install",
        "--upgrade",
        "auditwheel-emscripten",
        "build[virtualenv]",
        "pyodide-build",
        *constraint_flags(constraints_path),
        env=env,
    )

    pyodide_build_version = call(
        "python",
        "-c",
        "from importlib.metadata import version; print(version('pyodide-build'))",
        env=env,
        capture_stdout=True,
    ).strip()

    xbuildenv_info = get_xbuildenv_version_info(env, pyodide_version, pyodide_build_version)
    validate_pyodide_build_version(
        xbuildenv_info=xbuildenv_info,
        pyodide_build_version=pyodide_build_version,
    )

    emscripten_version = xbuildenv_info["emscripten"]
    log.step(f"Installing Emscripten version: {emscripten_version} ...")
    emcc_path = install_emscripten(tmp, emscripten_version)

    env["PATH"] = os.pathsep.join([str(emcc_path.parent), env["PATH"]])

    log.step(f"Installing Pyodide xbuildenv version: {pyodide_version} ...")
    env["PYODIDE_ROOT"] = install_xbuildenv(env, pyodide_build_version, pyodide_version)

    return env


def all_python_configurations() -> list[PythonConfiguration]:
    full_python_configs = resources.read_python_configs("pyodide")
    return [PythonConfiguration(**item) for item in full_python_configs]


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],  # noqa: ARG001
) -> list[PythonConfiguration]:
    return [c for c in all_python_configurations() if build_selector(c.identifier)]


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
                before_all_options.before_all, project=".", package=before_all_options.package_dir
            )
            shell(before_all_prepared, env=env)

        built_wheels: list[Path] = []

        for config in python_configurations:
            build_options = options.build_options(config.identifier)
            build_frontend = build_options.build_frontend or BuildFrontendConfig("build")

            if build_frontend.name == "pip":
                msg = "The pyodide platform doesn't support pip frontend"
                raise errors.FatalError(msg)

            log.build_start(config.identifier)

            identifier_tmp_dir = tmp_path / config.identifier

            built_wheel_dir = identifier_tmp_dir / "built_wheel"
            repaired_wheel_dir = identifier_tmp_dir / "repaired_wheel"
            identifier_tmp_dir.mkdir()
            built_wheel_dir.mkdir()
            repaired_wheel_dir.mkdir()

            constraints_path = build_options.dependency_constraints.get_for_python_version(
                version=config.version, variant="pyodide", tmp_dir=identifier_tmp_dir
            )

            env = setup_python(
                tmp=identifier_tmp_dir / "build",
                python_configuration=config,
                constraints_path=constraints_path,
                environment=build_options.environment,
                user_pyodide_version=build_options.pyodide_version,
            )
            pip_version = get_pip_version(env)
            # The Pyodide command line runner mounts all directories in the host
            # filesystem into the Pyodide file system, except for the custom
            # file systems /dev, /lib, /proc, and /tmp. Mounting the mount
            # points for alternate file systems causes some mysterious failure
            # of the process (it just quits without any clear error).
            #
            # Because of this, by default Pyodide can't see anything under /tmp.
            # This environment variable tells it also to mount our temp
            # directory.
            oldmounts = ""
            extra_mounts = [str(identifier_tmp_dir)]
            if Path.cwd().is_relative_to("/tmp"):
                extra_mounts.append(str(Path.cwd()))

            if "_PYODIDE_EXTRA_MOUNTS" in env:
                oldmounts = env["_PYODIDE_EXTRA_MOUNTS"] + ":"
            env["_PYODIDE_EXTRA_MOUNTS"] = oldmounts + ":".join(extra_mounts)

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)
            if compatible_wheel:
                log.step_end()
                print(
                    f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with {config.identifier}. Skipping build step..."
                )
                built_wheel = compatible_wheel
            else:
                if build_options.before_build:
                    log.step("Running before_build...")
                    before_build_prepared = prepare_command(
                        build_options.before_build, project=".", package=build_options.package_dir
                    )
                    shell(before_build_prepared, env=env)

                log.step("Building wheel...")

                extra_flags = get_build_frontend_extra_flags(
                    build_frontend, build_options.build_verbosity, build_options.config_settings
                )

                build_env = env.copy()
                if constraints_path:
                    combine_constraints(build_env, constraints_path, identifier_tmp_dir)
                build_env["VIRTUALENV_PIP"] = pip_version
                call(
                    "pyodide",
                    "build",
                    build_options.package_dir,
                    f"--outdir={built_wheel_dir}",
                    *extra_flags,
                    env=build_env,
                )
                built_wheel = next(built_wheel_dir.glob("*.whl"))

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

                repaired_wheel = next(repaired_wheel_dir.glob("*.whl"))

                if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                    raise errors.AlreadyBuiltWheelError(repaired_wheel.name)

            if build_options.test_command and build_options.test_selector(config.identifier):
                log.step("Testing wheel...")

                venv_dir = identifier_tmp_dir / "venv-test"
                # set up a virtual environment to install and test from, to make sure
                # there are no dependencies that were pulled in at build time.

                virtualenv_env = env.copy()
                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(ensure_node(config.node_version)),
                        virtualenv_env["PATH"],
                    ]
                )

                # pyodide venv uses virtualenv under the hood
                # use the pip embedded with virtualenv & disable network updates
                virtualenv_create_env = virtualenv_env.copy()
                virtualenv_create_env["VIRTUALENV_PIP"] = pip_version
                virtualenv_create_env["VIRTUALENV_NO_PERIODIC_UPDATE"] = "1"

                call("pyodide", "venv", venv_dir, env=virtualenv_create_env)

                virtualenv_env["PATH"] = os.pathsep.join(
                    [
                        str(venv_dir / "bin"),
                        virtualenv_env["PATH"],
                    ]
                )
                virtualenv_env["VIRTUAL_ENV"] = str(venv_dir)

                virtualenv_env = build_options.test_environment.as_dictionary(
                    prev_environment=virtualenv_env
                )

                # check that we are using the Python from the virtual environment
                call("which", "python", env=virtualenv_env)

                if build_options.before_test:
                    before_test_prepared = prepare_command(
                        build_options.before_test,
                        project=".",
                        package=build_options.package_dir,
                        wheel=repaired_wheel,
                    )
                    shell(before_test_prepared, env=virtualenv_env)

                # install the wheel
                call(
                    "pip",
                    "install",
                    f"{repaired_wheel}{build_options.test_extras}",
                    env=virtualenv_env,
                )

                # test the wheel
                if build_options.test_requires:
                    call("pip", "install", *build_options.test_requires, env=virtualenv_env)

                # run the tests from a temp dir, with an absolute path in the command
                # (this ensures that Python runs the tests against the installed wheel
                # and not the repo code)
                test_command_prepared = prepare_command(
                    build_options.test_command,
                    project=Path.cwd(),
                    package=build_options.package_dir.resolve(),
                )

                test_cwd = identifier_tmp_dir / "test_cwd"
                test_cwd.mkdir(exist_ok=True)

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

                shell(test_command_prepared, cwd=test_cwd, env=virtualenv_env)

            # we're all done here; move it to output (overwrite existing)
            if compatible_wheel is None:
                output_wheel = build_options.output_dir.joinpath(repaired_wheel.name)
                moved_wheel = move_file(repaired_wheel, output_wheel)
                if moved_wheel != output_wheel.resolve():
                    log.warning(
                        f"{repaired_wheel} was moved to {moved_wheel} instead of {output_wheel}"
                    )
                built_wheels.append(output_wheel)

    finally:
        pass
