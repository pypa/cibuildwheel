import argparse
import subprocess
import sys
import tarfile
import tempfile
import textwrap
from pathlib import Path

from cibuildwheel.util import format_safe


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cibuildwheel-from-sdist",
        description=textwrap.dedent(
            """
            Build wheels from an sdist archive.

            Extracts the sdist to a temp dir and calls cibuildwheel on the
            resulting package directory. Note that cibuildwheel will be
            invoked with its working directory as the package directory, so
            options aside from --output-dir and --config-file are relative to
            the package directory.
            """,
        ),
        epilog="Any further arguments will be passed on to cibuildwheel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--output-dir",
        default="wheelhouse",
        help="""
            Destination folder for the wheels. Default: wheelhouse.
        """,
    )

    parser.add_argument(
        "--config-file",
        default="",
        help="""
            TOML config file. To refer to a file inside the sdist, use the
            `{project}` or `{package}` placeholder. e.g. `--config-file
            {project}/config/cibuildwheel.toml` Default: "", meaning the
            pyproject.toml inside the sdist, if it exists.
        """,
    )

    parser.add_argument(
        "package",
        help="""
            Path to the sdist archive that you want wheels for. Must be a
            tar.gz archive file.
        """,
    )

    args, passthrough_args = parser.parse_known_args()

    output_dir = Path(args.output_dir).resolve()

    with tempfile.TemporaryDirectory(prefix="cibw-sdist-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        with tarfile.open(args.package) as tar:
            tar.extractall(path=temp_dir)

        temp_dir_contents = list(temp_dir.iterdir())

        if len(temp_dir_contents) != 1 or not temp_dir_contents[0].is_dir():
            exit("invalid sdist: didn't contain a single dir")

        project_dir = temp_dir_contents[0]

        if args.config_file:
            # expand the placeholders if they're used
            config_file_path = format_safe(
                args.config_file,
                project=project_dir,
                package=project_dir,
            )
            config_file = Path(config_file_path).resolve()
        else:
            config_file = None

        exit(
            subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "cibuildwheel",
                    *(["--config-file", str(config_file)] if config_file else []),
                    "--output-dir",
                    output_dir,
                    *passthrough_args,
                    ".",
                ],
                cwd=project_dir,
            )
        )


if __name__ == "__main__":
    main()
