from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest

import cibuildwheel.options
import cibuildwheel.selector
from cibuildwheel import errors
from cibuildwheel.environment import parse_environment
from cibuildwheel.frontend import BuildFrontendConfig
from cibuildwheel.oci_container import OCIContainerEngineConfig
from cibuildwheel.options import BuildOptions, GlobalOptions
from cibuildwheel.platforms import runner
from cibuildwheel.selector import BuildSelector
from cibuildwheel.util.packaging import DependencyConstraints


@pytest.fixture
def build_options(tmp_path: Path) -> BuildOptions:
    return BuildOptions(
        globals=GlobalOptions(
            package_dir=Path(),
            output_dir=tmp_path / "output",
            build_selector=BuildSelector(build_config="*", skip_config=""),
            test_selector=cibuildwheel.selector.TestSelector(skip_config=""),
            architectures=set(),
            allow_empty=False,
        ),
        environment=parse_environment(""),
        before_all="",
        before_build=None,
        xbuild_tools=None,
        xbuild_files={},
        repair_command="",
        manylinux_images=None,
        musllinux_images=None,
        dependency_constraints=DependencyConstraints.latest(),
        test_command=None,
        before_test=None,
        test_sources=[],
        test_requires=[],
        test_extras="",
        test_groups=[],
        test_environment=parse_environment(""),
        test_runtime=cibuildwheel.options.TestRuntimeConfig(),
        audit_requires=[],
        audit_command=[],
        build_verbosity=0,
        build_frontend=BuildFrontendConfig(name="build"),
        config_settings="",
        container_engine=OCIContainerEngineConfig(name="docker"),
        pyodide_version=None,
    )


class FakeBuilder:
    """Records the steps the runner invokes; touches no real files."""

    def __init__(
        self,
        *,
        identifier: str,
        build_options: BuildOptions,
        calls: list[tuple[str, str]],
        built_wheel_name: str = "spam-0.1.0-cp311-cp311-macosx_11_0_arm64.whl",
        repaired_wheel_names: tuple[str, ...] | None = None,
    ) -> None:
        self.identifier = identifier
        self.build_options = build_options
        self.calls = calls
        self.built_wheel_name = built_wheel_name
        self.repaired_wheel_names = repaired_wheel_names

    def record(self, step: str) -> None:
        self.calls.append((self.identifier, step))

    def setup(self) -> FakeBuilder:
        self.record("setup")
        return self

    @property
    def spec(self) -> runner.BuildSpec[Path]:
        return runner.BuildSpec(identifier=self.identifier, setup=self.setup)

    def before_build(self) -> None:
        self.record("before_build")

    def build_wheel(self) -> Path:
        self.record("build_wheel")
        return Path("/fake/built") / self.built_wheel_name

    def repair_wheel(self, built_wheel: Path) -> list[Path]:
        self.record("repair_wheel")
        names = (
            self.repaired_wheel_names
            if self.repaired_wheel_names is not None
            else (built_wheel.name,)
        )
        return [Path("/fake/repaired") / name for name in names]

    def audit_wheel(self, repaired_wheel: Path) -> None:  # noqa: ARG002
        self.record("audit_wheel")

    def test_wheel(self, repaired_wheel: Path) -> None:
        self.record(f"test_wheel:{repaired_wheel.name}")

    def move_to_output(self, repaired_wheel: Path) -> Path:
        self.record("move_to_output")
        return self.build_options.output_dir / repaired_wheel.name

    def cleanup(self) -> None:
        self.record("cleanup")


def test_step_order(build_options: BuildOptions) -> None:
    build_options = dataclasses.replace(
        build_options, before_build="make deps", test_command="pytest"
    )
    calls: list[tuple[str, str]] = []
    wheel_name = "spam-0.1.0-cp311-cp311-macosx_11_0_arm64.whl"
    builder = FakeBuilder(
        identifier="cp311-macosx_arm64",
        build_options=build_options,
        calls=calls,
        built_wheel_name=wheel_name,
    )

    runner.run_builds([builder.spec])

    assert calls == [
        ("cp311-macosx_arm64", "setup"),
        ("cp311-macosx_arm64", "before_build"),
        ("cp311-macosx_arm64", "build_wheel"),
        ("cp311-macosx_arm64", "repair_wheel"),
        ("cp311-macosx_arm64", "audit_wheel"),
        ("cp311-macosx_arm64", f"test_wheel:{wheel_name}"),
        ("cp311-macosx_arm64", "move_to_output"),
        ("cp311-macosx_arm64", "cleanup"),
    ]


def test_no_before_build_no_test(build_options: BuildOptions) -> None:
    calls: list[tuple[str, str]] = []
    builder = FakeBuilder(identifier="cp311-macosx_arm64", build_options=build_options, calls=calls)

    runner.run_builds([builder.spec])

    steps = [step for _, step in calls]
    assert "before_build" not in steps
    assert not any(step.startswith("test_wheel") for step in steps)
    assert steps == [
        "setup",
        "build_wheel",
        "repair_wheel",
        "audit_wheel",
        "move_to_output",
        "cleanup",
    ]


def test_compatible_wheel_reuse(build_options: BuildOptions) -> None:
    build_options = dataclasses.replace(build_options, test_command="pytest")
    calls: list[tuple[str, str]] = []
    abi3_wheel_name = "spam-0.1.0-cp311-abi3-macosx_11_0_arm64.whl"
    builders = [
        FakeBuilder(
            identifier="cp311-macosx_arm64",
            build_options=build_options,
            calls=calls,
            built_wheel_name=abi3_wheel_name,
        ),
        FakeBuilder(
            identifier="cp312-macosx_arm64",
            build_options=build_options,
            calls=calls,
        ),
    ]

    runner.run_builds([b.spec for b in builders])

    second = [step for identifier, step in calls if identifier == "cp312-macosx_arm64"]
    # build/repair/audit/move are skipped, but the reused wheel is still tested
    assert second == ["setup", f"test_wheel:{abi3_wheel_name}", "cleanup"]


def test_repair_produced_no_wheel(build_options: BuildOptions) -> None:
    builder = FakeBuilder(
        identifier="cp311-macosx_arm64",
        build_options=build_options,
        calls=[],
        repaired_wheel_names=(),
    )

    with pytest.raises(errors.RepairStepProducedNoWheelError):
        runner.run_builds([builder.spec])


def test_repair_produced_multiple_wheels(build_options: BuildOptions) -> None:
    builder = FakeBuilder(
        identifier="cp311-macosx_arm64",
        build_options=build_options,
        calls=[],
        repaired_wheel_names=(
            "spam-0.1.0-cp311-cp311-macosx_11_0_arm64.whl",
            "ham-0.1.0-cp311-cp311-macosx_11_0_arm64.whl",
        ),
    )

    with pytest.raises(errors.RepairStepProducedMultipleWheelsError):
        runner.run_builds([builder.spec])


def test_already_built_wheel(build_options: BuildOptions) -> None:
    # two identifiers producing the same (non-reusable) wheel name
    calls: list[tuple[str, str]] = []
    wheel_name = "spam-0.1.0-cp311-cp311-macosx_11_0_arm64.whl"
    builders = [
        FakeBuilder(
            identifier="cp311-macosx_arm64",
            build_options=build_options,
            calls=calls,
            built_wheel_name=wheel_name,
        ),
        FakeBuilder(
            identifier="cp311-macosx_x86_64",
            build_options=build_options,
            calls=calls,
            built_wheel_name=wheel_name,
        ),
    ]

    with pytest.raises(errors.AlreadyBuiltWheelError):
        runner.run_builds([b.spec for b in builders])


def test_none_any_wheel_rejected(build_options: BuildOptions) -> None:
    builder = FakeBuilder(
        identifier="cp311-macosx_arm64",
        build_options=build_options,
        calls=[],
        built_wheel_name="spam-0.1.0-py3-none-any.whl",
    )

    with pytest.raises(errors.NonPlatformWheelError):
        runner.run_builds([builder.spec])


def test_none_any_repaired_wheel_rejected(build_options: BuildOptions) -> None:
    builder = FakeBuilder(
        identifier="cp311-macosx_arm64",
        build_options=build_options,
        calls=[],
        repaired_wheel_names=("spam-0.1.0-py3-none-any.whl",),
    )

    with pytest.raises(errors.NonPlatformWheelError):
        runner.run_builds([builder.spec])


def test_test_skipped_by_selector(build_options: BuildOptions) -> None:
    build_options = dataclasses.replace(
        build_options,
        globals=dataclasses.replace(
            build_options.globals, test_selector=cibuildwheel.selector.TestSelector(skip_config="*")
        ),
        test_command="pytest",
    )
    calls: list[tuple[str, str]] = []
    builder = FakeBuilder(identifier="cp311-macosx_arm64", build_options=build_options, calls=calls)

    runner.run_builds([builder.spec])

    assert not any(step.startswith("test_wheel") for _, step in calls)


def test_fatal_on_called_process_error() -> None:
    with (
        pytest.raises(errors.FatalError, match="failed with code 42"),
        runner.fatal_on_called_process_error(),
    ):
        raise subprocess.CalledProcessError(42, ["false"])


def test_fatal_on_called_process_error_troubleshoot() -> None:
    seen: list[subprocess.CalledProcessError] = []
    with pytest.raises(errors.FatalError), runner.fatal_on_called_process_error(seen.append):
        raise subprocess.CalledProcessError(1, ["false"])
    assert len(seen) == 1


def test_prepare_test_cwd_sentinel(tmp_path: Path) -> None:
    test_cwd = tmp_path / "test_cwd"
    runner.prepare_test_cwd(test_cwd, [])
    assert "Please specify a path to your tests" in (test_cwd / "test_fail.py").read_text()


def test_prepare_test_cwd_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    (project / "tests").mkdir(parents=True)
    (project / "tests" / "test_spam.py").write_text("def test_spam(): pass\n")
    monkeypatch.chdir(project)

    test_cwd = tmp_path / "test_cwd"
    runner.prepare_test_cwd(test_cwd, ["tests"])

    assert (test_cwd / "tests" / "test_spam.py").exists()
    assert not (test_cwd / "test_fail.py").exists()
