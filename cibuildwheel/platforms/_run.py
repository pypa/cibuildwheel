"""Shared build driver for the "host" platforms.

The five non-container platforms (android, macos, windows, ios, pyodide) all run
their build phases directly on the build machine and share an identical
orchestration loop: run ``before_all`` once, then for each Python configuration
set up an environment, optionally build + repair + audit a wheel, optionally test
it, and move the result into the output directory.

That loop lives here, in :func:`run_host_build`, so each platform only has to
provide the platform-specific phase functions described by :class:`HostBackend`.
A platform satisfies the protocol simply by exposing module-level functions with
the right names (see ``android.py`` for the reference implementation).

Linux is deliberately *not* a host backend: it batches configurations by
container image and runs every phase through ``container.call`` inside an
``OCIContainer``, so it keeps its own bespoke loop.
"""

from __future__ import annotations

import enum
import subprocess

from cibuildwheel import errors
from cibuildwheel.audit import run_audit
from cibuildwheel.logger import log
from cibuildwheel.util.file import move_file
from cibuildwheel.util.packaging import find_compatible_wheel

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from typing import Protocol, TypeVar

    from cibuildwheel.architecture import Architecture
    from cibuildwheel.options import Options
    from cibuildwheel.selector import BuildSelector
    from cibuildwheel.typing import GenericPythonConfiguration

    ConfigT = TypeVar("ConfigT", bound=GenericPythonConfiguration)
    StateT = TypeVar("StateT")

    class HostBackend(Protocol[ConfigT, StateT]):
        """The phase functions every host platform must expose.

        ``StateT`` is an opaque, per-platform object (typically a frozen
        dataclass) created by :meth:`setup` and threaded through the remaining
        phases; the driver never inspects it.
        """

        def get_python_configurations(
            self, build_selector: BuildSelector, architectures: set[Architecture]
        ) -> Sequence[ConfigT]: ...

        def before_all(self, options: Options, configs: Sequence[ConfigT]) -> None: ...

        def setup(self, config: ConfigT, options: Options, tmp_path: Path) -> StateT: ...

        def before_build(self, state: StateT) -> None: ...

        def build_wheel(self, state: StateT) -> Path: ...

        def repair_wheel(self, state: StateT, built_wheel: Path) -> Path: ...

        def test_wheel(self, state: StateT, wheel: Path) -> None: ...

        def teardown(self, state: StateT) -> None: ...


class Stage(enum.Enum):
    BUILD = "build"
    TEST = "test"


ALL_STAGES = frozenset({Stage.BUILD, Stage.TEST})


def find_prebuilt_wheel(output_dir: Path, identifier: str) -> Path:
    """Locate a wheel in ``output_dir`` previously built for ``identifier``.

    Used by the test-only stage, which consumes wheels produced by an earlier
    build-only stage rather than building them itself.
    """
    wheel = find_compatible_wheel(sorted(output_dir.glob("*.whl")), identifier)
    if wheel is None:
        msg = f"No pre-built wheel for {identifier!r} found in {output_dir}"
        raise errors.FatalError(msg)
    return wheel


def run_host_build(
    backend: HostBackend[ConfigT, StateT],
    options: Options,
    tmp_path: Path,
    *,
    stages: frozenset[Stage] = ALL_STAGES,
) -> None:
    """Run the shared host build loop for ``backend``.

    ``stages`` selects which phases run: building (and repairing/auditing/moving
    the wheel) and/or testing. The default runs both, reproducing the historical
    behaviour exactly: the wheel is only moved into ``output_dir`` after a
    successful test, so a failing test leaves no wheel behind.
    """
    configs = backend.get_python_configurations(
        options.globals.build_selector, options.globals.architectures
    )
    if not configs:
        return

    try:
        if Stage.BUILD in stages:
            backend.before_all(options, configs)

        built_wheels: list[Path] = []
        for config in configs:
            log.build_start(config.identifier)
            build_options = options.build_options(config.identifier)
            state = backend.setup(config, options, tmp_path)

            compatible_wheel = find_compatible_wheel(built_wheels, config.identifier)

            if Stage.BUILD in stages:
                if compatible_wheel is not None:
                    print(
                        f"\nFound previously built wheel {compatible_wheel.name} that is "
                        f"compatible with {config.identifier}. Skipping build step..."
                    )
                    repaired_wheel = compatible_wheel
                else:
                    backend.before_build(state)
                    built_wheel = backend.build_wheel(state)
                    repaired_wheel = backend.repair_wheel(state, built_wheel)
                    if repaired_wheel.name in {w.name for w in built_wheels}:
                        raise errors.AlreadyBuiltWheelError(repaired_wheel.name)
                    run_audit(tmp_dir=tmp_path, build_options=build_options, wheel=repaired_wheel)
            else:
                # Test-only stage: consume a wheel built by an earlier run.
                repaired_wheel = find_prebuilt_wheel(build_options.output_dir, config.identifier)

            if Stage.TEST in stages:
                backend.test_wheel(state, repaired_wheel)

            output_wheel: Path | None = None
            if Stage.BUILD in stages and compatible_wheel is None:
                expected_wheel = build_options.output_dir / repaired_wheel.name
                output_wheel = move_file(repaired_wheel, expected_wheel)
                if output_wheel != expected_wheel.resolve():
                    log.warning(
                        f"{repaired_wheel} was moved to {output_wheel} instead of {expected_wheel}"
                    )
                built_wheels.append(output_wheel)

            backend.teardown(state)
            log.build_end(output_wheel)

    except subprocess.CalledProcessError as error:
        msg = f"Command {error.cmd} failed with code {error.returncode}. {error.stdout or ''}"
        raise errors.FatalError(msg) from error
