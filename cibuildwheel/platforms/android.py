import os
import shutil
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from build import ProjectBuilder
from filelock import FileLock

from .. import errors
from ..architecture import Architecture
from ..frontend import BuildFrontendConfig, get_build_frontend_extra_flags, parse_config_settings
from ..logger import log
from ..options import BuildOptions, Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import call, shell
from ..util.file import CIBW_CACHE_PATH, download, move_file
from ..util.helpers import prepare_command
from ..util.packaging import find_compatible_wheel
from ..venv import constraint_flags, virtualenv


def android_triplet(identifier: str) -> str:
    return {
        "arm64_v8a": "aarch64-linux-android",
        "x86_64": "x86_64-linux-android",
    }[identifier.split("_", 1)[1]]


@dataclass(frozen=True)
class PythonConfiguration:
    version: str
    identifier: str
    url: str


def all_python_configurations() -> list[PythonConfiguration]:
    return [PythonConfiguration(**item) for item in resources.read_python_configs("android")]


def get_python_configurations(
    build_selector: BuildSelector, architectures: set[Architecture]
) -> list[PythonConfiguration]:
    return [
        c
        for c in all_python_configurations()
        if any(c.identifier.endswith(f"-android_{arch.value}") for arch in architectures)
        and build_selector(c.identifier)
    ]


def shell_prepared(command: str, build_options: BuildOptions, env: dict[str, str]) -> None:
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
            before_all_options,
            before_all_options.environment.as_dictionary(os.environ),
        )


@dataclass
class Builder:
    config: PythonConfiguration
    build_options: BuildOptions
    tmp_dir: Path
    built_wheels: list[Path]

    def build(self) -> None:
        log.build_start(self.config.identifier)
        self.tmp_dir.mkdir()
        self.setup_python()

        compatible_wheel = find_compatible_wheel(self.built_wheels, self.config.identifier)
        if compatible_wheel:
            print(
                f"\nFound previously built wheel {compatible_wheel.name} that is "
                f"compatible with {self.config.identifier}. Skipping build step..."
            )
            repaired_wheel = compatible_wheel
        else:
            self.setup_env()
            self.before_build()
            repaired_wheel = self.build_wheel()

        self.test_wheel(repaired_wheel)
        if compatible_wheel is not None:
            self.built_wheels.append(
                move_file(repaired_wheel, self.build_options.output_dir / repaired_wheel.name)
            )

        shutil.rmtree(self.tmp_dir)
        log.build_end()

    def setup_python(self) -> None:
        log.step("Installing target Python...")
        python_tgz = CIBW_CACHE_PATH / self.config.url.rpartition("/")[-1]
        with FileLock(f"{python_tgz}.lock"):
            if not python_tgz.exists():
                download(self.config.url, python_tgz)

        self.python_dir = self.tmp_dir / "python"
        self.python_dir.mkdir()
        shutil.unpack_archive(python_tgz, self.python_dir)

    def setup_env(self) -> None:
        log.step("Setting up build environment...")

        python_exe_name = f"python{self.config.version}"
        python_exe = shutil.which(python_exe_name)
        if not python_exe:
            msg = f"Couldn't find {python_exe_name} on the PATH"
            raise errors.FatalError(msg)

        # Create virtual environment
        self.venv_dir = self.tmp_dir / "venv"
        dependency_constraint = self.build_options.dependency_constraints.get_for_python_version(
            version=self.config.version, tmp_dir=self.tmp_dir
        )
        self.env = virtualenv(
            self.config.version,
            Path(python_exe),
            self.venv_dir,
            dependency_constraint,
            use_uv=False,
        )

        # Apply custom environment variables, and check environment is still valid
        self.env = self.build_options.environment.as_dictionary(self.env)
        self.env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        for command in ["python", "pip"]:
            which = call("which", command, env=self.env, capture_stdout=True).strip()
            if which != f"{self.venv_dir}/bin/{command}":
                msg = (
                    "{command} available on PATH doesn't match our installed instance. If you "
                    "have modified PATH, ensure that you don't overwrite cibuildwheel's entry "
                    "or insert {command} above it."
                )
            call(command, "--version", env=self.env)

        # Install build tools
        self.build_frontend = self.build_options.build_frontend or BuildFrontendConfig("build")
        if self.build_frontend.name != "build":
            msg = "Android requires the build frontend to be 'build'"
            raise errors.FatalError(msg)
        self.pip_install("build", *constraint_flags(dependency_constraint))

        # Install build-time requirements. These must be installed for the build platform, not for
        # Android, which is why we can't allow them to be installed by the `build` subprocess.
        pb = ProjectBuilder(
            self.build_options.package_dir, python_executable=f"{self.venv_dir}/bin/python"
        )
        self.pip_install(*pb.build_system_requires)

        # get_requires_for_build runs the package's build script, so it must be called while
        # simulating Android.
        with self.simulate_android():
            requires_for_build = pb.get_requires_for_build(
                "wheel", parse_config_settings(self.build_options.config_settings)
            )
        self.pip_install(*requires_for_build)

    def pip_install(self, *args: str) -> None:
        if args:
            call("pip", "install", "--upgrade", *args, env=self.env)

    @contextmanager
    def simulate_android(self) -> Generator[None]:
        site_packages = self.venv_dir / f"lib/python{self.config.version}/site-packages"
        (site_packages / "_cross_venv.pth").write_text(
            f"import _cross_venv; _cross_venv.initialize('{self.config.identifier}')"
        )
        shutil.copy(resources.PATH / "_cross_venv.py", site_packages)

        env = self.env.copy()
        for line in call(
            self.python_dir / "android.py",
            "env",
            android_triplet(self.config.identifier),
            capture_stdout=True,
        ).splitlines():
            key, value = line.split("=", 1)
            env[key] = value

        original_env = {key: os.environ.get(key) for key in env}
        os.environ.update(env)

        try:
            yield
        finally:
            for name in ["_cross_venv.pth", "_cross_venv.py"]:
                (site_packages / name).unlink()

            for key, original_value in original_env.items():
                if original_value is None:
                    del os.environ[key]
                else:
                    os.environ[key] = original_value

    def before_build(self) -> None:
        if self.build_options.before_build:
            log.step("Running before_build...")
            shell_prepared(self.build_options.before_build, self.build_options, self.env)

    def build_wheel(self) -> Path:
        log.step("Building wheel...")
        built_wheel_dir = self.tmp_dir / "built_wheel"
        with self.simulate_android():
            call(
                "python",
                "-m",
                "build",
                self.build_options.package_dir,
                "--wheel",
                "--no-isolation",
                f"--outdir={built_wheel_dir}",
                *get_build_frontend_extra_flags(
                    self.build_frontend,
                    self.build_options.build_verbosity,
                    self.build_options.config_settings,
                ),
            )

        built_wheels = list(built_wheel_dir.glob("*.whl"))
        if len(built_wheels) != 1:
            msg = f"{built_wheel_dir} contains {len(built_wheels)} wheels; expected 1"
            raise errors.FatalError(msg)
        return built_wheels[0]

    def test_wheel(self, wheel: Path) -> None:
        if self.build_options.test_command and self.build_options.test_selector(
            self.config.identifier
        ):
            log.step("Testing wheel...")
            print("FIXME", wheel)
            # TODO pass environment from cibuildwheel config?
            # TODO require pip 25.1 for Android tag support


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
            Builder(
                config,
                options.build_options(config.identifier),
                tmp_path / config.identifier,
                built_wheels,
            ).build()

    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
