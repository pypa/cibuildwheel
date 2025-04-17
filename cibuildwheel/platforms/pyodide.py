import functools
import os
import shutil
import sys
import tomllib
from collections.abc import Set
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

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
from ..util.helpers import prepare_command
from ..util.packaging import combine_constraints, find_compatible_wheel, get_pip_version
from ..venv import constraint_flags, virtualenv

IS_WIN: Final[bool] = sys.platform.startswith("win")


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    pyodide_version: str
    pyodide_build_version: str
    emscripten_version: str
    node_version: str


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
    # We don't need to match the emsdk version to the version we install, but
    # we do for stability
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


def install_xbuildenv(env: dict[str, str], pyodide_build_version: str, pyodide_version: str) -> str:
    """Install a particular Pyodide xbuildenv version and set a path to the Pyodide root."""
    # Since pyodide-build was unvendored from Pyodide v0.27.0, the versions of pyodide-build are
    # not guaranteed to match the versions of Pyodide or be in sync with them. Hence, we shall
    # specify the pyodide-build version in the root path, which will set up the xbuildenv for
    # the requested Pyodide version.
    pyodide_root = (
        CIBW_CACHE_PATH
        / f".pyodide-xbuildenv-{pyodide_build_version}/{pyodide_version}/xbuildenv/pyodide-root"
    )
    with FileLock(CIBW_CACHE_PATH / "xbuildenv.lock"):
        if pyodide_root.exists():
            return str(pyodide_root)

        # We don't want to mutate env but we need to delete any existing
        # PYODIDE_ROOT so copy it first.
        env = dict(env)
        env.pop("PYODIDE_ROOT", None)
        call(
            "pyodide",
            "xbuildenv",
            "install",
            pyodide_version,
            env=env,
            cwd=CIBW_CACHE_PATH,
        )
    return str(pyodide_root)


def get_base_python(identifier: str) -> Path:
    implementation_id = identifier.split("-")[0]
    majorminor = implementation_id[len("cp") :]
    version_info = (int(majorminor[0]), int(majorminor[1:]))
    if version_info == sys.version_info[:2]:
        return Path(sys.executable)

    major_minor = ".".join(str(v) for v in version_info)
    python_name = f"python{major_minor}"
    which_python = shutil.which(python_name)
    if which_python is None:
        msg = f"CPython {major_minor} is not installed."
        raise errors.FatalError(msg)
    return Path(which_python)


def setup_python(
    tmp: Path,
    python_configuration: PythonConfiguration,
    constraints_path: Path | None,
    environment: ParsedEnvironment,
) -> dict[str, str]:
    base_python = get_base_python(python_configuration.identifier)

    log.step("Setting up build environment...")
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

    log.step(f"Installing Emscripten version: {python_configuration.emscripten_version} ...")
    emcc_path = install_emscripten(tmp, python_configuration.emscripten_version)

    env["PATH"] = os.pathsep.join([str(emcc_path.parent), env["PATH"]])

    log.step(f"Installing Pyodide xbuildenv version: {python_configuration.pyodide_version} ...")
    env["PYODIDE_ROOT"] = install_xbuildenv(
        env, python_configuration.pyodide_build_version, python_configuration.pyodide_version
    )

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
                identifier_tmp_dir / "build",
                config,
                constraints_path,
                build_options.environment,
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

                # check that we are using the Python from the virtual environment
                call("which", "python", env=virtualenv_env)

                if build_options.before_test:
                    before_test_prepared = prepare_command(
                        build_options.before_test,
                        project=".",
                        package=build_options.package_dir,
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

                if build_options.test_sources:
                    test_cwd = identifier_tmp_dir / "test_cwd"
                    test_cwd.mkdir(exist_ok=True)
                    copy_test_sources(
                        build_options.test_sources,
                        build_options.package_dir,
                        test_cwd,
                    )
                else:
                    # There are no test sources. Run the tests in the project directory.
                    test_cwd = Path.cwd()

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
