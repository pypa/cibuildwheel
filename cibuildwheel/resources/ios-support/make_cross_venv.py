from __future__ import annotations

__lazy_modules__ = {"importlib", "json", "pprint", "shutil", "typing"}

import json
import pprint
import shutil
import sys
from importlib import util as importlib_util
from pathlib import Path
from typing import Any


def localized_vars(orig_vars: dict[str, Any], slice_path: Path) -> dict[str, Any]:
    """Update (where possible) any references to build-time variables with the
    best guess of the installed location.
    """
    # The host's sysconfigdata will include references to build-time variables.
    # Update these to refer to the current known install location.
    orig_prefix = orig_vars["prefix"]
    localized_vars = {}
    for key, value in orig_vars.items():
        final = value
        if isinstance(value, str):
            # Replace any reference to the build installation prefix
            final = final.replace(orig_prefix, str(slice_path))
            # Replace any reference to the build-time Framework location
            final = final.replace("-F .", f"-F {slice_path}")
        localized_vars[key] = final

    return localized_vars


def localize_sysconfigdata(sysconfig_path: Path, venv_site_packages: Path) -> None:
    """Localize a sysconfigdata python module.

    :param sysconfig_path: The platform config that contains the
        sysconfigdata module to localize.
    :param venv_site_packages: The site packages folder where the localized
        sysconfigdata module should be output.
    """
    # Find the "_sysconfigdata_*.py" file in the platform config
    sysconfigdata_path = next(sysconfig_path.glob("_sysconfigdata_*.py"))

    # Import the sysconfigdata module
    spec = importlib_util.spec_from_file_location(sysconfigdata_path.stem, sysconfigdata_path)
    if spec is None:
        msg = f"Unable to load spec for {sysconfigdata_path}"
        raise ValueError(msg)
    if spec.loader is None:
        msg = f"Spec for {sysconfigdata_path} does not define a loader"
        raise ValueError(msg)
    sysconfigdata = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(sysconfigdata)

    # Write the updated sysconfigdata module into the cross-platform site.
    slice_path = sysconfigdata_path.parent.parent.parent
    with (venv_site_packages / sysconfigdata_path.name).open("w") as f:
        f.write(f"# Generated from {sysconfigdata_path}\n")
        f.write("build_time_vars = ")
        pprint.pprint(
            localized_vars(sysconfigdata.build_time_vars, slice_path), stream=f, compact=True
        )


def localize_sysconfig_vars(sysconfig_path: Path, venv_site_packages: Path) -> None:
    """Localize a sysconfig_vars.json file.

    :param sysconfig_path: The platform config that contains the
        sysconfigdata module to localize.
    :param venv_site_packages: The site-packages folder where the localized
        sysconfig_vars.json file should be output.
    """
    # Find the "_sysconfig_vars_*.json" file in the platform config
    sysconfig_vars_path = next(sysconfig_path.glob("_sysconfig_vars_*.json"))

    with sysconfig_vars_path.open("rb") as f:
        build_time_vars = json.load(f)

    slice_path = sysconfig_vars_path.parent.parent.parent
    with (venv_site_packages / sysconfig_vars_path.name).open("w") as f:
        json.dump(localized_vars(build_time_vars, slice_path), f, indent=2)


def make_cross_venv(
    venv_path: Path,
    sysconfig_path: Path,
    platform_config_path: Path,
) -> None:
    """Convert a virtual environment into a cross-platform environment.

    :param venv_path: The path to the root of the venv.
    :param sysconfig_path: The path containing sysconfigdata files for the
        target platform.
    :param platform_config_path: The path containing the cross-venv support
        scripts (_cross_venv.py and the multiarch-specific _cross_*.py).
    """
    if not venv_path.exists():
        msg = f"Virtual environment {venv_path} does not exist."
        raise ValueError(msg)
    if not (venv_path / "bin/python3").exists():
        msg = f"{venv_path} does not appear to be a virtual environment."
        raise ValueError(msg)

    LIB_PATH = f"lib/python{sys.version_info[0]}.{sys.version_info[1]}"

    # Derive the multiarch tag from the sysconfigdata filename if available;
    # otherwise fall back to the directory name (BeeWare convention).
    sysconfigdata_files = list(sysconfig_path.glob("_sysconfigdata_*.py"))
    if sysconfigdata_files:
        multiarch_tag = sysconfigdata_files[0].stem.split("_ios_")[1]
        cross_multiarch = f"_cross_{multiarch_tag.replace('-', '_')}"
    else:
        multiarch_tag = sysconfig_path.name
        cross_multiarch = f"_cross_{multiarch_tag.replace('-', '_')}"

    print(
        f"Converting {venv_path} into a {multiarch_tag} environment... ",
        end="",
    )

    # Update path references in the sysconfigdata to reflect local conditions.
    venv_site_packages = venv_path / LIB_PATH / "site-packages"
    localize_sysconfigdata(sysconfig_path, venv_site_packages)
    localize_sysconfig_vars(sysconfig_path, venv_site_packages)
    # The multiarch-specific script may be directly in platform_config_path (BeeWare
    # convention, where all files are co-located) or in a named subdirectory
    # (cibuildwheel resource layout, where each multiarch has its own subdir).
    multiarch_script = platform_config_path / f"{cross_multiarch}.py"
    if not multiarch_script.exists():
        multiarch_script = platform_config_path / multiarch_tag / f"{cross_multiarch}.py"
    shutil.copy(
        multiarch_script,
        venv_site_packages / f"{cross_multiarch}.py",
    )
    shutil.copy(
        platform_config_path / "_cross_venv.py",
        venv_site_packages / "_cross_venv.py",
    )
    # Write the .pth file that will enable the cross-env modifications
    (venv_site_packages / "_cross_venv.pth").write_text(
        f"import {cross_multiarch}; import _cross_venv\n"
    )

    print("done.")


if __name__ == "__main__":
    try:
        sysconfig_path = Path(sys.argv[2]).resolve()
    except IndexError:
        sysconfig_path = Path(__file__).parent

    try:
        platform_config_path = Path(sys.argv[3]).resolve()
    except IndexError:
        platform_config_path = sysconfig_path

    try:
        venv_path = Path(sys.argv[1]).resolve()
        make_cross_venv(venv_path, sysconfig_path, platform_config_path)
    except IndexError:
        print("""
Convert a virtual environment into a cross-platform environment.

Usage:
    make_cross_venv <venv> (<sysconfig path>) (<platform config path>)

The sysconfig path is the path that contains the `_sysconfigdata-*.py` file
for the platform being targeted. If an explicit sysconfig path isn't
provided, it is assumed the directory containing the make_cross_venv script
also contains the sysconfig data for the interpreter.

The platform config path is the path that contains the cross-venv support
scripts. If an explicit platform config path isn't provided, it is assumed
that the sysconfig path also contains the platform configuration files.
""")
