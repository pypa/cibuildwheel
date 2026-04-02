"""
Audit step for wheels built by cibuildwheel.

This module provides functionality to run audit commands (like abi3audit)
on built wheels after all platform builds are complete.
"""

import subprocess
import sys
from pathlib import Path

from cibuildwheel import errors
from cibuildwheel.logger import log
from cibuildwheel.options import BuildOptions
from cibuildwheel.util.cmd import call, shell
from cibuildwheel.util.helpers import prepare_command
from cibuildwheel.util.packaging import is_abi3_wheel
from cibuildwheel.venv import activate_virtualenv, virtualenv


def run_audit(
    *,
    tmp_dir: Path,
    build_options: BuildOptions,
    wheel: Path,
) -> None:
    """
    Run the audit commands on a single wheel.

    Creates a virtualenv (or reuses an existing one) and installs any
    audit requirements, then runs each audit command template against
    the wheel. Commands containing {abi3_wheel} are skipped for
    non-abi3 wheels.
    """

    if not needs_audit(build_options.audit_command, wheel.name):
        return

    log.step("Auditing wheel...")

    audit_venv_dir = tmp_dir / "audit_venv"
    if not audit_venv_dir.exists():
        audit_venv_dir.mkdir(parents=True, exist_ok=True)

        use_uv = build_options.build_frontend.name in {"uv", "build[uv]"}
        dependency_constraint = build_options.dependency_constraints.get_for_python_version(
            version=sys.version, tmp_dir=tmp_dir
        )

        env = virtualenv(
            sys.version,
            Path(sys.executable),
            audit_venv_dir,
            dependency_constraint=dependency_constraint,
            use_uv=use_uv,
        )
    else:
        env = activate_virtualenv(audit_venv_dir)

    # install audit requirements. This is run every time in case the user has
    # defined overrides.
    audit_requires = build_options.audit_requires
    if audit_requires:
        print(f"Installing audit dependencies: {', '.join(audit_requires)}")

        pip = ["uv", "pip"] if use_uv else ["pip"]
        # we pin if the audit-requires is left as the default "abi3audit"
        should_pin = audit_requires == ["abi3audit"] and dependency_constraint

        call(
            *pip,
            "install",
            *(["--constraint", str(dependency_constraint)] if should_pin else []),
            *audit_requires,
            env=env,
        )

    audit_command = build_options.audit_command

    for command_template in audit_command:
        if "{abi3_wheel}" in command_template and "{wheel}" in command_template:
            msg = (
                f"Invalid audit command {command_template!r}: cannot contain both {{abi3_wheel}} "
                "and {{wheel}} placeholders"
            )
            raise errors.ConfigurationError(msg)

        if "{abi3_wheel}" in command_template and not is_abi3_wheel(wheel.name):
            continue

        prepared_command = prepare_command(
            command_template,
            abi3_wheel=wheel,
            wheel=wheel,
            project=".",
            package=build_options.package_dir,
        )

        print(f"Running audit command: {prepared_command}")
        try:
            shell(prepared_command, env=env)
        except subprocess.CalledProcessError as e:
            print(f"Audit command failed with exit code {e.returncode}")
            msg = f"Audit command failed: {prepared_command}"
            raise errors.AuditCommandFailedError(msg) from e


def needs_audit(audit_commands: list[str], wheel_name: str) -> bool:
    saw_abi3_placeholder = False
    for audit_command in audit_commands:
        if "{abi3_wheel}" in audit_command:
            saw_abi3_placeholder = True
            if is_abi3_wheel(wheel_name):
                return True
        elif "{wheel}" in audit_command:
            return True

    if saw_abi3_placeholder:
        print("No audit required for this wheel, as it is not abi3")
    else:
        print("No audit configured")

    return False
