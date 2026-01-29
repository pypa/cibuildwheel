#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    # CIBW_HOST_TRIPLET is set in the android_env to the Android target triplet.
    target = os.environ.get("CIBW_HOST_TRIPLET")

    cmd_name = Path(sys.argv[0]).name

    # Find the real command in PATH, excluding the current script's directory
    path_env = os.environ.get("PATH", "")
    script_dir = Path(__file__).resolve().parent

    paths = path_env.split(os.pathsep)
    # Filter out the script directory to avoid recursion
    filtered_paths = [p for p in paths if Path(p).resolve() != script_dir]
    filtered_path_env = os.pathsep.join(filtered_paths)

    real_cmd = shutil.which(cmd_name, path=filtered_path_env)

    if not real_cmd:
        sys.stderr.write(f"cibuildwheel: Error: Could not find system {cmd_name}\n")
        sys.exit(1)

    # If we have a target (i.e. we are in the android_env), try to install it.
    if target:
        # Check if rustup is available to install the target
        rustup_path = shutil.which("rustup", path=filtered_path_env)

        if rustup_path:
            try:
                # We call rustup to ensure the target is installed.
                subprocess.run(
                    [rustup_path, "target", "add", target],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                sys.stderr.write(
                    f"cibuildwheel: Error: Failed to install Rust target {target}: {e.stderr}\n"
                )
                sys.exit(1)

    # Execute the real command
    os.execv(real_cmd, [real_cmd, *sys.argv[1:]])


if __name__ == "__main__":
    main()
