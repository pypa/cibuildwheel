from __future__ import annotations

import pytest

from cibuildwheel.platforms.macos import rosetta_arch_prefix


@pytest.mark.parametrize(
    ("machine_arch", "target_arch", "expected"),
    [
        # arm64 host building x86_64 -> needs Rosetta prefix
        ("arm64", "x86_64", ["arch", "-x86_64"]),
        # native cases -> no prefix
        ("arm64", "arm64", []),
        ("x86_64", "x86_64", []),
        # x86_64 host targeting arm64 is unsupported and handled separately;
        # the helper itself just returns no prefix.
        ("x86_64", "arm64", []),
    ],
)
def test_rosetta_arch_prefix(machine_arch: str, target_arch: str, expected: list[str]) -> None:
    assert rosetta_arch_prefix(machine_arch=machine_arch, target_arch=target_arch) == expected  # type: ignore[arg-type]
