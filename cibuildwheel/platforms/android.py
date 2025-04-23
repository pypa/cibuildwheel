import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock

from .. import errors
from ..architecture import Architecture
from ..logger import log
from ..options import BuildOptions, Options
from ..selector import BuildSelector
from ..util import resources
from ..util.cmd import shell
from ..util.file import CIBW_CACHE_PATH, download, move_file
from ..util.helpers import prepare_command
from ..util.packaging import find_compatible_wheel


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


def shell_prepared(build_options: BuildOptions, command: str) -> None:
    shell(
        prepare_command(command, project=".", package=build_options.package_dir),
        env=build_options.environment.as_dictionary(os.environ),
    )


def before_all(options: Options, python_configurations: list[PythonConfiguration]) -> None:
    before_all_options = options.build_options(python_configurations[0].identifier)
    if before_all_options.before_all:
        log.step("Running before_all...")
        shell_prepared(before_all_options, before_all_options.before_all)


@dataclass
class Builder:
    config: PythonConfiguration
    build_options: BuildOptions
    tmp_path: Path
    built_wheels: list[Path]

    def build(self) -> None:
        log.build_start(self.config.identifier)
        self.tmp_path.mkdir()
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

        shutil.rmtree(self.tmp_path)
        log.build_end()

    def setup_python(self) -> None:
        log.step("Installing target Python...")
        python_tgz = CIBW_CACHE_PATH / self.config.url.rpartition("/")[-1]
        with FileLock(f"{python_tgz}.lock"):
            if not python_tgz.exists():
                download(self.config.url, python_tgz)

        self.python_path = self.tmp_path / "python"
        self.python_path.mkdir()
        shutil.unpack_archive(python_tgz, self.python_path)

    def setup_env(self) -> None:
        log.step("Setting up build environment...")
        # TODO

    def before_build(self) -> None:
        if self.build_options.before_build:
            log.step("Running before_build...")
            # TODO must run in the build environment
            shell_prepared(self.build_options, self.build_options.before_build)

    def build_wheel(self) -> Path:
        log.step("Building wheel...")
        built_wheel_dir = self.tmp_path / "built_wheel"

        # TODO

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
