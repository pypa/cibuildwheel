from __future__ import annotations

__lazy_modules__ = {
    "cibuildwheel.architecture",
    "cibuildwheel.frontend",
    "cibuildwheel.logger",
    "cibuildwheel.util",
    "cibuildwheel.util.cmd",
    "cibuildwheel.util.file",
    "cibuildwheel.util.helpers",
    "cibuildwheel.util.packaging",
    "cibuildwheel.util.python_build_standalone",
    "cibuildwheel.venv",
    "filelock",
    "json",
    "pathlib",
    "tempfile",
    "tomllib",
}

import dataclasses
import functools
import json
import os
import sys
import tomllib
import typing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, TypedDict

from filelock import FileLock

from cibuildwheel import errors
from cibuildwheel.architecture import Architecture
from cibuildwheel.frontend import get_build_frontend_extra_flags, prepare_config_settings
from cibuildwheel.logger import log
from cibuildwheel.platforms import runner
from cibuildwheel.util import resources
from cibuildwheel.util.cmd import call, shell
from cibuildwheel.util.file import (
    CIBW_CACHE_PATH,
    download,
    extract_tar,
    extract_zip,
    remove_on_error,
)
from cibuildwheel.util.helpers import prepare_command, unwrap, unwrap_preserving_paragraphs
from cibuildwheel.util.packaging import get_pip_version
from cibuildwheel.util.python_build_standalone import (
    PythonBuildStandaloneError,
    create_python_build_standalone_environment,
)
from cibuildwheel.venv import constraint_flags, virtualenv

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Set

    from cibuildwheel.environment import ParsedEnvironment
    from cibuildwheel.options import BuildOptions, Options
    from cibuildwheel.selector import BuildSelector

IS_WIN: Final[bool] = sys.platform.startswith("win")


@dataclasses.dataclass(frozen=True, kw_only=True)
class PythonConfiguration:
    version: str
    identifier: str
    default_pyodide_version: str
    node_version: str
    sha256: str = ""


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
                with remove_on_error(path):
                    if ext == "zip":
                        extract_zip(archive, path.parent)
                    else:
                        extract_tar(archive, path.parent)
    assert path.exists()
    if not IS_WIN:
        return path / "bin"
    return path


def install_emscripten(env: dict[str, str], version: str, xbuildenv_cache_path: Path) -> Path:
    """Install Emscripten via pyodide-build, which also applies Pyodide-specific patches."""
    emscripten_dir = Path(
        call("pyodide", "config", "get", "emscripten_dir", env=env, capture_stdout=True).strip()
    )
    with FileLock(CIBW_CACHE_PATH / "emscripten.lock"):
        if emscripten_dir.exists():
            return emscripten_dir
        with remove_on_error(emscripten_dir):
            call(
                "pyodide",
                "xbuildenv",
                "install-emscripten",
                "--force",
                "--version",
                version,
                "--path",
                str(xbuildenv_cache_path),
                env=env,
                cwd=CIBW_CACHE_PATH,
            )
    assert emscripten_dir.exists()
    return emscripten_dir


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

    return typing.cast("list[PyodideXBuildEnvInfo]", xbuildenvs_info["environments"])


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


def validate_pyodide_target_python(
    xbuildenv_info: PyodideXBuildEnvInfo, python_configuration: PythonConfiguration
) -> None:
    """
    Validate that the resolved Pyodide xbuildenv targets the same Python version
    as the identifier being built.

    This is to catch the case where a global ``pyodide-version`` is applied to an
    identifier whose Python version does not match, such as setting
    ``pyodide-version = "3Y.0.0"`` (a Python 3.Y environment) while
    building ``cp3X-pyodide_wasm32``.
    """
    xbuildenv_version = xbuildenv_info["version"]
    identifier = python_configuration.identifier
    expected_version = python_configuration.version
    default_version = python_configuration.default_pyodide_version
    xbuildenv_python_minor = ".".join(xbuildenv_info["python"].split(".")[:2])
    if xbuildenv_python_minor != expected_version:
        msg = unwrap_preserving_paragraphs(f"""
            The `pyodide-version` option is set to {xbuildenv_version}, which
            provides Python {xbuildenv_python_minor}, but the {identifier} build
            needs Python {expected_version}.

            Either remove `pyodide-version` so {identifier} uses its default
            ({default_version}), or stop building {identifier} so that
            `pyodide-version` only applies to an identifier it matches.
        """)
        raise errors.ConfigurationError(msg)


def install_xbuildenv(env: dict[str, str], xbuildenv_cache_path: Path, pyodide_version: str) -> str:
    """Install a particular Pyodide xbuildenv version and set a path to the Pyodide root."""
    pyodide_root = xbuildenv_cache_path / pyodide_version / "xbuildenv" / "pyodide-root"

    with FileLock(CIBW_CACHE_PATH / "xbuildenv.lock"):
        if pyodide_root.exists():
            return str(pyodide_root)

        # We don't want to mutate env but we need to delete any existing
        # PYODIDE_ROOT so copy it first.
        env = dict(env)
        env.pop("PYODIDE_ROOT", None)

        # Install the xbuildenv
        with remove_on_error(xbuildenv_cache_path / pyodide_version):
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
    call("python", "-V", "-V", env=env)

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
    validate_pyodide_target_python(
        xbuildenv_info=xbuildenv_info,
        python_configuration=python_configuration,
    )

    xbuildenv_cache_path = CIBW_CACHE_PATH / f"pyodide-build-{pyodide_build_version}"

    log.step(f"Installing Pyodide xbuildenv version: {pyodide_version} ...")
    env["PYODIDE_ROOT"] = install_xbuildenv(env, xbuildenv_cache_path, pyodide_version)

    emscripten_version = xbuildenv_info["emscripten"]
    log.step(
        f"Installing Emscripten {emscripten_version} and applying Pyodide-specific patches ..."
    )
    emscripten_dir = install_emscripten(env, emscripten_version, xbuildenv_cache_path)

    env["PATH"] = os.pathsep.join([str(emscripten_dir), env["PATH"]])

    return env


def all_python_configurations() -> list[PythonConfiguration]:
    full_python_configs = resources.read_python_configs("pyodide")
    return [PythonConfiguration(**item) for item in full_python_configs]


def get_python_configurations(
    build_selector: BuildSelector,
    architectures: Set[Architecture],  # noqa: ARG001
) -> list[PythonConfiguration]:
    return [c for c in all_python_configurations() if build_selector(c.identifier)]


class PyodideBuilder(runner.HostBuilder):
    def __init__(
        self,
        *,
        config: PythonConfiguration,
        build_options: BuildOptions,
        tmp_dir: Path,
        session_tmp_dir: Path,
    ) -> None:
        super().__init__(
            identifier=config.identifier,
            build_options=build_options,
            tmp_dir=tmp_dir,
            session_tmp_dir=session_tmp_dir,
        )
        self.config = config

    def setup(self) -> None:
        build_options = self.build_options

        self.tmp_dir.mkdir()
        self.built_wheel_dir.mkdir()

        constraints_path = build_options.dependency_constraints.get_for_python_version(
            version=self.config.version, variant="pyodide", tmp_dir=self.tmp_dir
        )

        env = setup_python(
            tmp=self.tmp_dir / "build",
            python_configuration=self.config,
            constraints_path=constraints_path,
            environment=build_options.environment,
            user_pyodide_version=build_options.pyodide_version,
        )
        env["CIBUILDWHEEL_BUILD_IDENTIFIER"] = self.identifier
        self.pip_version = get_pip_version(env)

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
        extra_mounts = [str(self.tmp_dir)]
        if Path.cwd().is_relative_to("/tmp"):
            extra_mounts.append(str(Path.cwd()))

        if "_PYODIDE_EXTRA_MOUNTS" in env:
            oldmounts = env["_PYODIDE_EXTRA_MOUNTS"] + ":"
        env["_PYODIDE_EXTRA_MOUNTS"] = oldmounts + ":".join(extra_mounts)

        self.env = env

    def build_wheel(self) -> Path:
        build_options = self.build_options

        extra_flags = get_build_frontend_extra_flags(
            build_options.build_frontend,
            build_options.build_verbosity,
            prepare_config_settings(
                build_options.config_settings,
                project=Path.cwd(),
                package=build_options.package_dir,
            ),
        )

        call(
            "pyodide",
            "build",
            build_options.package_dir,
            f"--outdir={self.built_wheel_dir}",
            *extra_flags,
            env=self.env,
        )
        try:
            return next(self.built_wheel_dir.glob("*.whl"))
        except StopIteration:
            raise errors.BuildProducedNoWheelError() from None

    def test_wheel(self, repaired_wheel: Path) -> None:
        build_options = self.build_options
        assert build_options.test_command is not None

        log.step("Testing wheel...")

        # set up a virtual environment to install and test from, to make sure
        # there are no dependencies that were pulled in at build time.
        venv_dir = self.tmp_dir / "venv-test"

        virtualenv_env = self.env.copy()
        virtualenv_env["PATH"] = os.pathsep.join(
            [
                str(ensure_node(self.config.node_version)),
                virtualenv_env["PATH"],
            ]
        )

        # pyodide venv uses virtualenv under the hood
        # use the pip embedded with virtualenv & disable network updates
        virtualenv_create_env = virtualenv_env.copy()
        virtualenv_create_env["VIRTUALENV_PIP"] = self.pip_version
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
            wheel=repaired_wheel,
        )

        test_cwd = self.tmp_dir / "test_cwd"
        runner.prepare_test_cwd(test_cwd, build_options.test_sources)

        shell(test_command_prepared, cwd=test_cwd, env=virtualenv_env)


def build(options: Options, tmp_path: Path) -> None:
    python_configurations = get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )

    if not python_configurations:
        return

    with runner.fatal_on_called_process_error():
        runner.run_before_all(options, python_configurations)
        runner.run_builds(
            [
                PyodideBuilder(
                    config=config,
                    build_options=options.build_options(config.identifier),
                    tmp_dir=tmp_path / config.identifier,
                    session_tmp_dir=tmp_path,
                )
                for config in python_configurations
            ]
        )
