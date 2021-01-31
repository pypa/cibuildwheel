import toml
from packaging.version import Version

from cibuildwheel.extra import InlineArrayDictEncoder  # noqa: E402
from cibuildwheel.util import resources_dir


def test_compare_configs():
    with open(resources_dir / "build-platforms.toml") as f:
        txt = f.read()

    dict_txt = toml.loads(txt)

    new_txt = toml.dumps(dict_txt, encoder=InlineArrayDictEncoder())
    print(new_txt)

    assert new_txt == txt


def test_dump_with_Version():
    example = {
        "windows": {
            "python_configurations": [
                {"identifier": "cp27-win32", "version": Version("2.7.18"), "arch": "32"},
                {"identifier": "cp27-win_amd64", "version": Version("2.7.18"), "arch": "64"},
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

    output = toml.dumps(example, encoder=InlineArrayDictEncoder())
    print(output)
    assert output == result
