import importlib
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path


def main():
    parser = ArgumentParser(
        prog="python -m test.test_projects", description="Generate a test project to check it out"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated project in a file explorer",
    )
    parser.add_argument(
        "PROJECT",
        help="Python path to a project object. E.g. test.test_0_basic.basic_project",
    )
    parser.add_argument(
        "OUTPUT",
        nargs="?",
        help="Path to output dir. If no dir is passed, a tempdir will be generated.",
    )
    options = parser.parse_args()

    module, _, name = options.PROJECT.rpartition(".")

    project = getattr(importlib.import_module(module), name)

    project_dir = Path(options.OUTPUT or tempfile.mkdtemp())
    project.generate(project_dir)

    print("Project generated at", project_dir)
    print()

    if options.open:
        if sys.platform == "darwin":
            subprocess.run(["open", "--", project_dir], check=True)
        elif sys.platform == "linux2":
            subprocess.run(["xdg-open", "--", project_dir], check=True)
        elif sys.platform == "win32":
            subprocess.run(["explorer", project_dir], check=True)


if __name__ == "__main__":
    main()
