"""
The shared build loop, used by every platform module.

Each platform defines a builder class implementing the Builder protocol, whose
methods are the platform-specific steps of one wheel build. run_builds() takes
a BuildSpec per build identifier and drives the steps in a fixed order:

    setup -> before_build -> build_wheel -> repair_wheel -> audit_wheel
          -> test_wheel -> move_to_output -> cleanup

A builder is only constructed once its environment is fully set up: each
BuildSpec carries a setup function that does the work and returns the
ready-to-use builder, so every attribute on a builder is set from the moment
it exists.

run_builds() also owns everything that's identical across platforms: logging,
reuse of compatible wheels, validation of the built/repaired wheels, the test
gate, and moving wheels to the output directory. The host_*() functions are
the step implementations shared by the platforms that build directly on the
host (everything except Linux); builders use them by delegation.
"""

from __future__ import annotations

__lazy_modules__ = {
    "cibuildwheel.audit",
    "cibuildwheel.logger",
    "cibuildwheel.util",
    "cibuildwheel.util.cmd",
    "cibuildwheel.util.file",
    "cibuildwheel.util.helpers",
    "cibuildwheel.util.packaging",
    "shutil",
    "subprocess",
}

import contextlib
import dataclasses
import os
import shutil
import subprocess
from pathlib import Path, PurePath
from typing import Generic, Protocol, TypeVar

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


class Builder(Protocol[PathT]):
    """
    The platform-specific steps to build one wheel (one build identifier).

    Builders are plain classes (typically frozen dataclasses) satisfying this
    protocol structurally; they are created by a BuildSpec's setup function
    with all their state already prepared. run_builds() calls the steps in a
    fixed order. PathT is the type of the paths the wheels live at while
    building: Path on the host platforms, PurePosixPath inside the Linux
    container.
    """

    @property
    def identifier(self) -> str: ...

    @property
    def build_options(self) -> BuildOptions: ...

    def before_build(self) -> None:
        """Run the user's before-build command. Only called if one is set."""

    def build_wheel(self) -> PathT:
        """Build the wheel with the configured frontend and return its path."""

    def repair_wheel(self, built_wheel: PathT) -> list[PathT]:
        """Run the user's repair command (or, if none is set, move the wheel
        as-is) and return the contents of the repaired-wheel directory. The
        runner validates that exactly one wheel was produced."""

    def audit_wheel(self, repaired_wheel: PathT) -> None:
        """Run the audit command, if one is configured."""

    def test_wheel(self, repaired_wheel: PathT) -> None:
        """Test the wheel: set up a test environment, run before-test, install
        the wheel and its test requirements, and run the test command. Only
        called if a test command is set and the test selector matches. Skip
        conditions that can only be determined at build time (e.g. an arch
        that can't be tested on this machine) live here too."""

    def move_to_output(self, repaired_wheel: PathT) -> PathT:
        """Move the wheel to the output directory, returning the path that
        later builds can reuse it from (and install it from, in tests)."""

    def cleanup(self) -> None:
        """Remove this identifier's temporary files."""


@dataclasses.dataclass(frozen=True, kw_only=True)
class BuildSpec(Generic[PathT]):
    """One wheel to build: its identifier, plus a setup function that installs
    Python, prepares the build environment, and returns the builder that runs
    the remaining steps. setup logs its own log.step()s and may leave the last
    one open."""

    identifier: str
    setup: Callable[[], Builder[PathT]]


class HostBuilder(Builder[Path], Protocol):
    """The state the shared host_*() step implementations need on a builder
    that builds directly on the host (every platform except Linux)."""

    @property
    def tmp_dir(self) -> Path:
        """Per-identifier scratch space, removed by cleanup()."""

    @property
    def session_tmp_dir(self) -> Path:
        """Shared across identifiers; run_audit() reuses its venv between
        calls."""

    @property
    def repaired_wheel_dir(self) -> Path: ...


def host_before_build(builder: HostBuilder, *, env: dict[str, str]) -> None:
    assert builder.build_options.before_build is not None
    before_build_prepared = prepare_command(
        builder.build_options.before_build,
        project=".",
        package=builder.build_options.package_dir,
    )
    shell(before_build_prepared, env=env)


def host_repair_wheel(
    builder: HostBuilder, built_wheel: Path, *, env: dict[str, str]
) -> list[Path]:
    builder.repaired_wheel_dir.mkdir(exist_ok=True)
    if builder.build_options.repair_command:
        repair_command_prepared = prepare_command(
            builder.build_options.repair_command,
            wheel=built_wheel,
            dest_dir=builder.repaired_wheel_dir,
            package=builder.build_options.package_dir,
            project=".",
        )
        shell(repair_command_prepared, env=env)
    else:
        shutil.move(str(built_wheel), builder.repaired_wheel_dir)
    return list(builder.repaired_wheel_dir.glob("*.whl"))


def host_audit_wheel(builder: HostBuilder, repaired_wheel: Path) -> None:
    run_audit(
        tmp_dir=builder.session_tmp_dir, build_options=builder.build_options, wheel=repaired_wheel
    )


def host_move_to_output(builder: HostBuilder, repaired_wheel: Path) -> Path:
    output_wheel = builder.build_options.output_dir / repaired_wheel.name
    moved_wheel = move_file(repaired_wheel, output_wheel)
    if moved_wheel != output_wheel.resolve():
        log.warning(f"{repaired_wheel} was moved to {moved_wheel} instead of {output_wheel}")
    return output_wheel


def host_cleanup(builder: HostBuilder) -> None:
    # ignore_errors: occasionally Windows fails to unlink a file, and we
    # don't want to abort a build because of a leftover temp dir
    shutil.rmtree(builder.tmp_dir, ignore_errors=True)


def run_builds(specs: Sequence[BuildSpec[PathT]]) -> None:
    """Build a wheel for each spec, in order."""
    built_wheels: list[PathT] = []

    for spec in specs:
        log.build_start(spec.identifier)

        builder = spec.setup()
        build_options = builder.build_options

        compatible_wheel = find_compatible_wheel(built_wheels, spec.identifier)
        if compatible_wheel is not None:
            log.step_end()
            print(
                f"\nFound previously built wheel {compatible_wheel.name}, that's compatible with "
                f"{spec.identifier}. Skipping build step..."
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

        if build_options.test_command and build_options.test_selector(spec.identifier):
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
