import contextlib
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cibuildwheel import errors
from cibuildwheel.audit import needs_audit, run_audit


def mock_virtualenv() -> contextlib.AbstractContextManager[Mock]:
    return patch(
        "cibuildwheel.audit.virtualenv",
        return_value={
            "PATH": "/bin",
            "VIRTUAL_ENV": "/tmp/v",
        },
    )


class TestNeedsAudit:
    def test_empty_commands(self) -> None:
        assert needs_audit([], "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl") is False

    def test_wheel_placeholder_matches_any_wheel(self) -> None:
        assert needs_audit(
            ["my-tool {wheel}"], "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        )

    def test_abi3_placeholder_skips_non_abi3(self) -> None:
        assert (
            needs_audit(
                ["abi3audit {abi3_wheel}"], "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
            )
            is False
        )

    def test_abi3_placeholder_matches_abi3(self) -> None:
        assert needs_audit(
            ["abi3audit {abi3_wheel}"], "example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"
        )

    def test_mixed_commands_matches_if_any_applies(self) -> None:
        commands = ["abi3audit {abi3_wheel}", "twine check {wheel}"]
        # non-abi3 wheel still needs audit because of the {wheel} command
        assert needs_audit(commands, "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl")


class TestRunAudit:
    @pytest.fixture
    def mock_build_options(self) -> Mock:
        opts = Mock()
        opts.audit_command = []
        opts.audit_requires = []
        opts.package_dir = Path("/fake/package")
        opts.build_frontend.name = "build"
        opts.dependency_constraints.get_for_python_version.return_value = None
        return opts

    def test_no_commands_does_nothing(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = []

        with patch("cibuildwheel.audit.shell") as mock_shell:
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
            mock_shell.assert_not_called()

    def test_runs_wheel_command(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["my-tool {wheel}"]

        with mock_virtualenv(), patch("cibuildwheel.audit.shell") as mock_shell:
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
            mock_shell.assert_called_once()
            cmd = mock_shell.call_args[0][0]
            assert str(wheel) in cmd

    def test_abi3_command_skipped_for_non_abi3(
        self, tmp_path: Path, mock_build_options: Mock
    ) -> None:
        wheel = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["abi3audit {abi3_wheel}"]

        with patch("cibuildwheel.audit.shell") as mock_shell:
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
            mock_shell.assert_not_called()

    def test_abi3_command_runs_for_abi3(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["abi3audit {abi3_wheel}"]

        with (
            mock_virtualenv(),
            patch("cibuildwheel.audit.shell") as mock_shell,
        ):
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
            mock_shell.assert_called_once()
            cmd = mock_shell.call_args[0][0]
            assert str(wheel) in cmd

    def test_raises_on_command_failure(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["failing-tool {wheel}"]

        with (
            mock_virtualenv(),
            patch(
                "cibuildwheel.audit.shell",
                side_effect=subprocess.CalledProcessError(1, "failing-tool"),
            ),
            pytest.raises(errors.AuditCommandFailedError),
        ):
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)

    def test_multiple_commands_all_run(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp310-cp310-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["tool-a {wheel}", "tool-b {wheel}"]

        with (
            mock_virtualenv(),
            patch("cibuildwheel.audit.shell") as mock_shell,
        ):
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
            assert mock_shell.call_count == 2

    def test_both_placeholders_raises(self, tmp_path: Path, mock_build_options: Mock) -> None:
        wheel = tmp_path / "example-1.0.0-cp38-abi3-manylinux_2_17_x86_64.whl"
        mock_build_options.audit_command = ["my-tool {wheel} {abi3_wheel}"]

        with (
            mock_virtualenv(),
            pytest.raises(errors.ConfigurationError, match="cannot contain both"),
        ):
            run_audit(tmp_dir=tmp_path, build_options=mock_build_options, wheel=wheel)
