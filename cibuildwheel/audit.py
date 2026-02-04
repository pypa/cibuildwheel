"""
Audit step for wheels built by cibuildwheel.

This module provides functionality to run audit commands (like abi3audit)
on built wheels after all platform builds are complete.
"""

import os
import subprocess
from pathlib import Path

from packaging.utils import parse_wheel_filename

from .logger import log
from .util.helpers import format_safe


def is_abi3_wheel(wheel_path: Path) -> bool:
    """Check if a wheel is an abi3 wheel by parsing its filename."""
    _, _, _, tags = parse_wheel_filename(wheel_path.name)
    return any(t.abi == "abi3" for t in tags)


def run_audit(
    audit_command: str,
    output_dir: Path,
    wheels_before: set[str],
) -> None:
    """
    Run the audit command on wheels built in this run.

    The audit command supports the following placeholders:
    - {wheel}: expands to each wheel path, runs the command once per wheel
    - {abi3_wheel}: same as {wheel}, but only for abi3 wheels

    If the command contains {abi3_wheel} but no abi3 wheels were produced,
    the audit step is skipped.

    Args:
        audit_command: The command template to run
        output_dir: Directory where wheels were output
        wheels_before: Set of wheel filenames that existed before the build
    """
    if not audit_command:
        return

    # Find wheels built in this run (new wheels that weren't there before)
    all_wheels = sorted(output_dir.glob("*.whl"))
    just_built = [w for w in all_wheels if w.name not in wheels_before]

    if not just_built:
        return

    # Determine if we're auditing abi3 wheels only
    abi3_only = "{abi3_wheel}" in audit_command

    # Filter wheels if needed
    if abi3_only:
        wheels_to_audit = [w for w in just_built if is_abi3_wheel(w)]
        if not wheels_to_audit:
            log.step("Skipping audit step (no abi3 wheels produced)")
            return
    else:
        wheels_to_audit = just_built

    log.step("Running audit...")

    for wheel in wheels_to_audit:
        # Prepare command with placeholders
        prepared = format_safe(
            audit_command,
            wheel=wheel,
            abi3_wheel=wheel,
        )

        log.step(f"  Auditing {wheel.name}...")
        env = os.environ.copy()

        try:
            subprocess.run(
                prepared,
                shell=True,
                check=True,
                env=env,
                cwd=output_dir,
            )
        except subprocess.CalledProcessError as e:
            log.error(f"Audit command failed for {wheel.name}")
            raise SystemExit(e.returncode) from e
