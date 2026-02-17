from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cibuildwheel.util.packaging import is_abi3_wheel, run_abi3audit


class TestIsAbi3Wheel:
    def test_abi3_wheel(self):
        assert is_abi3_wheel("foo-1.0-cp310-abi3-manylinux_2_28_x86_64.whl") is True

    def test_abi3_wheel_macos(self):
        assert is_abi3_wheel("foo-1.0-cp311-abi3-macosx_11_0_arm64.whl") is True

    def test_abi3_wheel_windows(self):
        assert is_abi3_wheel("foo-1.0-cp310-abi3-win_amd64.whl") is True

    def test_cpython_wheel(self):
        assert is_abi3_wheel("foo-1.0-cp310-cp310-manylinux_2_28_x86_64.whl") is False

    def test_none_any_wheel(self):
        assert is_abi3_wheel("foo-1.0-py3-none-any.whl") is False

    def test_none_platform_wheel(self):
        assert is_abi3_wheel("foo-1.0-cp310-none-win_amd64.whl") is False


class TestRunAbi3audit:
    def test_skips_non_abi3_wheel(self):
        wheel = Path("/tmp/foo-1.0-cp310-cp310-manylinux_2_28_x86_64.whl")
        with patch("cibuildwheel.util.packaging.subprocess.run") as mock_run:
            run_abi3audit(wheel)
            mock_run.assert_not_called()

    def test_runs_on_abi3_wheel(self):
        wheel = Path("/tmp/foo-1.0-cp310-abi3-manylinux_2_28_x86_64.whl")
        with patch("cibuildwheel.util.packaging.subprocess.run") as mock_run:
            run_abi3audit(wheel)
            mock_run.assert_called_once_with(
                [sys.executable, "-m", "abi3audit", "--strict", "--report", str(wheel)],
                check=True,
            )

    def test_raises_on_failure(self):
        wheel = Path("/tmp/foo-1.0-cp310-abi3-manylinux_2_28_x86_64.whl")
        with (
            patch(
                "cibuildwheel.util.packaging.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "abi3audit"),
            ),
            pytest.raises(subprocess.CalledProcessError),
        ):
            run_abi3audit(wheel)
