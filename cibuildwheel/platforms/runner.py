"""
The shared build loop, used by every platform module.

Each platform defines a Builder subclass whose methods implement the
platform-specific steps; run_builds() drives those steps for each build
identifier, in a fixed order:

    setup -> before_build -> build_wheel -> repair_wheel -> audit_wheel
          -> test_wheel -> move_to_output -> cleanup

run_builds() also owns everything that's identical across platforms: logging,
reuse of compatible wheels, validation of the built/repaired wheels, the test
gate, and moving wheels to the output directory.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path, PurePath
from typing import Generic, TypeVar

from cibuildwheel import errors
from cibuildwheel.audit import run_audit
from cibuildwheel.logger import log
from cibuildwheel.util import resources
from cibuildwheel.util.cmd import shell
from cibuildwheel.util.file import copy_test_sources, move_file
from cibuildwheel.util.helpers import prepare_command
from cibuildwheel.util.packaging import find_compatible_wheel

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping, Sequence

    from cibuildwheel.options import BuildOptions, Options
    from cibuildwheel.typing import GenericPythonConfiguration

PathT = TypeVar("PathT", bound=PurePath)


class Builder(ABC, Generic[PathT]):
    """
    The platform-specific steps to build one wheel (one build identifier).

    Constructing a Builder must not do any work; all work happens in the step
    methods, which run_builds() calls in a fixed order. PathT is the type of
    the paths the wheels live at while building: Path on the host platforms,
    PurePosixPath inside the Linux container.
    """

    identifier: str
    build_options: BuildOptions

    @abstractmethod
    def setup(self) -> None:
        """Install Python and prepare the build environment, storing any state
        the later steps need (e.g. self.env) on the instance. Logs its own
        log.step()s and may leave the last one open."""

    @abstractmethod
    def before_build(self) -> None:
        """Run the user's before-build command. Only called if one is set."""

    @abstractmethod
    def build_wheel(self) -> PathT:
        """Build the wheel with the configured frontend and return its path."""

    @abstractmethod
    def repair_wheel(self, built_wheel: PathT) -> list[PathT]:
        """Run the user's repair command (or, if none is set, move the wheel
        as-is) and return the contents of the repaired-wheel directory. The
        runner validates that exactly one wheel was produced."""

    @abstractmethod
    def audit_wheel(self, repaired_wheel: PathT) -> None:
        """Run the audit command, if one is configured."""

    @abstractmethod
    def test_wheel(self, repaired_wheel: PathT) -> None:
        """Test the wheel: set up a test environment, run before-test, install
        the wheel and its test requirements, and run the test command. Only
        called if a test command is set and the test selector matches. Skip
        conditions that can only be determined at build time (e.g. an arch
        that can't be tested on this machine) live here too."""

    @abstractmethod
    def move_to_output(self, repaired_wheel: PathT) -> PathT:
        """Move the wheel to the output directory, returning the path that
        later builds can reuse it from (and install it from, in tests)."""

    @abstractmethod
    def cleanup(self) -> None:
        """Remove this identifier's temporary files."""


class HostBuilder(Builder[Path]):
    """A Builder whose wheels live on the host filesystem; implements the
    steps that are common to every platform except Linux (which builds inside
    a container)."""

    env: dict[str, str]  # set by setup() in each subclass

    def __init__(
        self,
        *,
        identifier: str,
        build_options: BuildOptions,
        tmp_dir: Path,
        session_tmp_dir: Path,
    ) -> None:
        self.identifier = identifier
        self.build_options = build_options
        # per-identifier scratch space, removed by cleanup()
        self.tmp_dir = tmp_dir
        # shared across identifiers; run_audit() reuses its venv between calls
        self.session_tmp_dir = session_tmp_dir
        self.built_wheel_dir = tmp_dir / "built_wheel"
        self.repaired_wheel_dir = tmp_dir / "repaired_wheel"

    def before_build(self) -> None:
        assert self.build_options.before_build is not None
        before_build_prepared = prepare_command(
            self.build_options.before_build,
            project=".",
            package=self.build_options.package_dir,
        )
        shell(before_build_prepared, env=self.env)

    def repair_wheel(self, built_wheel: Path) -> list[Path]:
        self.repaired_wheel_dir.mkdir(exist_ok=True)
        if self.build_options.repair_command:
            repair_command_prepared = prepare_command(
                self.build_options.repair_command,
                wheel=built_wheel,
                dest_dir=self.repaired_wheel_dir,
                package=self.build_options.package_dir,
                project=".",
            )
            shell(repair_command_prepared, env=self.env)
        else:
            shutil.move(str(built_wheel), self.repaired_wheel_dir)
        return list(self.repaired_wheel_dir.glob("*.whl"))

    def audit_wheel(self, repaired_wheel: Path) -> None:
        run_audit(
            tmp_dir=self.session_tmp_dir, build_options=self.build_options, wheel=repaired_wheel
        )

    def move_to_output(self, repaired_wheel: Path) -> Path:
        output_wheel = self.build_options.output_dir / repaired_wheel.name
        moved_wheel = move_file(repaired_wheel, output_wheel)
        if moved_wheel != output_wheel.resolve():
            log.warning(f"{repaired_wheel} was moved to {moved_wheel} instead of {output_wheel}")
        return output_wheel

    def cleanup(self) -> None:
        # ignore_errors: occasionally Windows fails to unlink a file, and we
        # don't want to abort a build because of a leftover temp dir
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


def run_builds(builders: Sequence[Builder[PathT]]) -> None:
    """Build a wheel for each builder, in order."""
    built_wheels: list[PathT] = []

    for builder in builders:
        build_options = builder.build_options
        log.build_start(builder.identifier)

        builder.setup()

        compatible_wheel = find_compatible_wheel(built_wheels, builder.identifier)
        if compatible_wheel is not None:
            log.step_end()
            print(
                f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with "
                f"{builder.identifier}. Skipping build step..."
            )
            repaired_wheel = compatible_wheel
        else:
            if build_options.before_build:
                log.step("Running before_build...")
                builder.before_build()

            log.step("Building wheel...")
            built_wheel = builder.build_wheel()
            if built_wheel.name.endswith("none-any.whl"):
                raise errors.NonPlatformWheelError()

            if build_options.repair_command:
                log.step("Repairing wheel...")
            repaired_wheels = builder.repair_wheel(built_wheel)
            match repaired_wheels:
                case [only_wheel]:
                    repaired_wheel = only_wheel
                case []:
                    raise errors.RepairStepProducedNoWheelError()
                case many_wheels:
                    raise errors.RepairStepProducedMultipleWheelsError(
                        [wheel.name for wheel in many_wheels]
                    )

            if repaired_wheel.name in {wheel.name for wheel in built_wheels}:
                raise errors.AlreadyBuiltWheelError(repaired_wheel.name)
            log.step_end()

            builder.audit_wheel(repaired_wheel)

        if build_options.test_command and build_options.test_selector(builder.identifier):
            builder.test_wheel(repaired_wheel)

        output_wheel: Path | None = None
        if compatible_wheel is None:
            tracked_wheel = builder.move_to_output(repaired_wheel)
            built_wheels.append(tracked_wheel)
            # on Linux, the wheel only arrives at this host path when the
            # container exits; the summary reads the file lazily, so that's fine
            output_wheel = build_options.output_dir / tracked_wheel.name

        builder.cleanup()
        log.build_end(output_wheel)


def run_before_all(
    options: Options,
    python_configurations: Sequence[GenericPythonConfiguration],
    *,
    env_defaults: Mapping[str, str] | None = None,
) -> None:
    """Run the user's before-all command on the host, if one is set."""
    before_all_options = options.build_options(python_configurations[0].identifier)
    if not before_all_options.before_all:
        return

    log.step("Running before_all...")
    env = before_all_options.environment.as_dictionary(prev_environment=os.environ)
    for name, value in (env_defaults or {}).items():
        env.setdefault(name, value)
    before_all_prepared = prepare_command(
        before_all_options.before_all, project=".", package=before_all_options.package_dir
    )
    shell(before_all_prepared, env=env)


@contextlib.contextmanager
def fatal_on_called_process_error(
    troubleshoot: Callable[[subprocess.CalledProcessError], None] | None = None,
) -> Generator[None, None, None]:
    """Turn a failed command anywhere in the build into a FatalError."""
    try:
        yield
    except subprocess.CalledProcessError as error:
        if troubleshoot is not None:
            troubleshoot(error)
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error


def prepare_test_cwd(test_cwd: Path, test_sources: list[str]) -> None:
    """Populate the directory the test command runs in: the user's test
    sources if configured, otherwise a sentinel test that fails with a
    helpful message if the user's test command assumes the project dir."""
    test_cwd.mkdir(exist_ok=True)
    if test_sources:
        copy_test_sources(test_sources, Path.cwd(), test_cwd)
    else:
        (test_cwd / "test_fail.py").write_text(resources.TEST_FAIL_CWD_FILE.read_text())
