from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.version import Version

from cibuildwheel.extra import Printable, dump_python_configurations
from cibuildwheel.util import resources_dir


def test_compare_configs():
    with open(resources_dir / "build-platforms.toml") as f1:
        txt = f1.read()

    with open(resources_dir / "build-platforms.toml", "rb") as f2:
        dict_txt = tomllib.load(f2)

    new_txt = dump_python_configurations(dict_txt)
    print(new_txt)

    assert new_txt == txt


def test_dump_with_Version():
    # MyPy doesn't understand deeply nested dicts correctly
    example: dict[str, dict[str, list[dict[str, Printable]]]] = {
        "windows": {
            "python_configurations": [
                {"identifier": "cp27-win32", "version": Version("2.7.18"), "arch": "32"},
                {"identifier": "cp27-win_amd64", "version": "2.7.18", "arch": "64"},
            ]
        }
    }

    result = """\
[windows]
python_configurations = [
  { identifier = "cp27-win32", version = "2.7.18", arch = "32" },
  { identifier = "cp27-win_amd64", version = "2.7.18", arch = "64" },
]
"""

    output = dump_python_configurations(example)
    print(output)
    assert output == result
