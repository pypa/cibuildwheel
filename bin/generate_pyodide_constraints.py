#!/usr/bin/env python3

import sys
import textwrap
from pathlib import Path

import click

from cibuildwheel.extra import get_pyodide_xbuildenv_info


@click.command()
@click.argument(
    "pyodide-version",
    type=str,
)
@click.option(
    "--output-file",
    type=click.Path(),
    default=None,
    help="Output file to write the constraints to. If not provided, the constraints will be printed to stdout.",
)
def generate_pyodide_constraints(pyodide_version: str, output_file: str | None = None) -> None:
    """
    Generate constraints for a specific Pyodide version. The constraints are
    generated based on the Pyodide version's xbuildenv info, which is retrieved
    from the Pyodide repository.

    These constraints should then be 'pinned' using `uv pip compile`.

    Example usage:

        bin/generate_pyodide_constraints.py 0.27.0
    """
    xbuildenv_info = get_pyodide_xbuildenv_info()
    try:
        pyodide_version_xbuildenv_info = xbuildenv_info["releases"][pyodide_version]
    except KeyError as e:
        msg = f"Pyodide version {pyodide_version} not found in xbuildenv info. Versions available: {', '.join(xbuildenv_info['releases'].keys())}"
        raise click.BadParameter(msg) from e

    pyodide_build_min_version = pyodide_version_xbuildenv_info.get("min_pyodide_build_version")
    pyodide_build_max_version = pyodide_version_xbuildenv_info.get("max_pyodide_build_version")

    pyodide_build_specifier_parts: list[str] = []

    if pyodide_build_min_version:
        pyodide_build_specifier_parts.append(f">={pyodide_build_min_version}")
    if pyodide_build_max_version:
        pyodide_build_specifier_parts.append(f"<={pyodide_build_max_version}")

    pyodide_build_specifier = ",".join(pyodide_build_specifier_parts)

    constraints_txt = textwrap.dedent(f"""
        pip
        build[virtualenv]
        pyodide-build{pyodide_build_specifier}
        click<8.2
    """)

    if output_file is None:
        print(constraints_txt)
    else:
        Path(output_file).write_text(constraints_txt)
        print(f"Constraints written to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    generate_pyodide_constraints()
