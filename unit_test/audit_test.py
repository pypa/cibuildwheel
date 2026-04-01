from pathlib import Path

import pytest

from cibuildwheel.audit import is_abi3_wheel, run_audit


class TestIsAbi3Wheel:
    def test_abi3_wheel(self) -> None:
        assert is_abi3_wheel(Path("example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"))

    def test_abi3_wheel_macos(self) -> None:
        assert is_abi3_wheel(Path("example-1.0.0-cp39-abi3-macosx_10_9_x86_64.whl"))

    def test_abi3_wheel_windows(self) -> None:
        assert is_abi3_wheel(Path("example-1.0.0-cp310-abi3-win_amd64.whl"))

    def test_non_abi3_wheel(self) -> None:
        assert not is_abi3_wheel(Path("example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"))

    def test_pure_python_wheel(self) -> None:
        assert not is_abi3_wheel(Path("example-1.0.0-py3-none-any.whl"))


class TestRunAudit:
    def test_empty_command_does_nothing(self, tmp_path: Path) -> None:
        # Create a wheel file
        wheel_path = tmp_path / "example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Should not raise and should be a no-op
        run_audit(
            audit_command="",
            output_dir=tmp_path,
            wheels_before=set(),
        )

    def test_audit_runs_on_new_wheels(self, tmp_path: Path) -> None:
        # Create a wheel file (simulating a build)
        wheel_path = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Create a marker file to verify command ran
        marker = tmp_path / "audit_ran.txt"

        run_audit(
            audit_command=f"touch {marker}",
            output_dir=tmp_path,
            wheels_before=set(),
        )

        assert marker.exists()

    def test_audit_skips_old_wheels(self, tmp_path: Path) -> None:
        # Create a wheel file
        wheel_path = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Create a marker file to verify command ran
        marker = tmp_path / "audit_ran.txt"

        # Pre-existing wheel should be skipped
        run_audit(
            audit_command=f"touch {marker}",
            output_dir=tmp_path,
            wheels_before={wheel_path.name},
        )

        assert not marker.exists()

    def test_abi3_only_mode_skips_non_abi3(self, tmp_path: Path) -> None:
        # Create a non-abi3 wheel
        wheel_path = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Create a marker file to verify command ran
        marker = tmp_path / "audit_ran.txt"

        run_audit(
            audit_command=f"echo {{abi3_wheel}} && touch {marker}",
            output_dir=tmp_path,
            wheels_before=set(),
        )

        # Should not run because no abi3 wheels
        assert not marker.exists()

    def test_abi3_only_mode_runs_on_abi3(self, tmp_path: Path) -> None:
        # Create an abi3 wheel
        wheel_path = tmp_path / "example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Create a marker file to verify command ran
        marker = tmp_path / "audit_ran.txt"

        run_audit(
            audit_command=f"echo {{abi3_wheel}} && touch {marker}",
            output_dir=tmp_path,
            wheels_before=set(),
        )

        assert marker.exists()

    def test_wheel_placeholder_expanded(self, tmp_path: Path) -> None:
        # Create a wheel file
        wheel_path = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        # Write wheel path to a file to verify expansion
        output_file = tmp_path / "wheel_path.txt"

        run_audit(
            audit_command=f"echo {{wheel}} > {output_file}",
            output_dir=tmp_path,
            wheels_before=set(),
        )

        assert output_file.exists()
        content = output_file.read_text().strip()
        assert content == str(wheel_path)

    def test_audit_fails_on_error(self, tmp_path: Path) -> None:
        # Create a wheel file
        wheel_path = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        wheel_path.touch()

        with pytest.raises(SystemExit) as exc_info:
            run_audit(
                audit_command="exit 1",
                output_dir=tmp_path,
                wheels_before=set(),
            )

        assert exc_info.value.code == 1
