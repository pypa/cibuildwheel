import tomllib

from packaging.version import Version

from cibuildwheel.extra import Printable, dump_python_configurations
from cibuildwheel.util import resources


def test_compare_configs():
    txt = resources.BUILD_PLATFORMS.read_text()

    with resources.BUILD_PLATFORMS.open("rb") as f2:
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
