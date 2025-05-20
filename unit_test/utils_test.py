import textwrap
from pathlib import PurePath
from unittest.mock import Mock, call

import pytest

from cibuildwheel import errors
from cibuildwheel.ci import fix_ansi_codes_for_github_actions
from cibuildwheel.util.file import copy_test_sources
from cibuildwheel.util.helpers import (
    FlexibleVersion,
    format_safe,
    parse_key_value_string,
    prepare_command,
    unwrap,
    unwrap_preserving_paragraphs,
)
from cibuildwheel.util.packaging import find_compatible_wheel


def test_format_safe():
    assert format_safe("{wheel}", wheel="filename.whl") == "filename.whl"
    assert format_safe("command #{wheel}", wheel="filename.whl") == "command {wheel}"
    assert format_safe("{command #{wheel}}", wheel="filename.whl") == "{command {wheel}}"

    # check unmatched brackets
    assert format_safe("{command {wheel}", wheel="filename.whl") == "{command filename.whl"

    # check positional-style arguments i.e. {}
    assert (
        format_safe("find . -name  * -exec ls -a {} \\;", project="/project")
        == "find . -name  * -exec ls -a {} \\;"
    )

    assert format_safe("{param} {param}", param="1") == "1 1"
    assert format_safe("# {param} {param}", param="1") == "# 1 1"
    assert format_safe("#{not_a_param} {param}", param="1") == "#{not_a_param} 1"


def test_prepare_command():
    assert prepare_command("python -m {project}", project="project") == "python -m project"
    assert prepare_command("python -m {something}", project="project") == "python -m {something}"
    assert (
        prepare_command("python -m {something.abc}", project="project")
        == "python -m {something.abc}"
    )

    assert (
        prepare_command("python -m {something.abc[4]:3f}", project="project")
        == "python -m {something.abc[4]:3f}"
    )

    # test backslashes in the replacement
    assert (
        prepare_command(
            "command {wheel} \\Users\\Temp\\output_dir", wheel="\\Temporary Files\\cibw"
        )
        == "command \\Temporary Files\\cibw \\Users\\Temp\\output_dir"
    )

    # test some unusual syntax that used to trip up the str.format approach
    assert (
        prepare_command("{a}{a,b}{b:.2e}{c}{d%s}{e:3}{f[0]}", a="42", b="3.14159")
        == "42{a,b}{b:.2e}{c}{d%s}{e:3}{f[0]}"
    )


@pytest.mark.parametrize(
    ("wheel", "identifier"),
    [
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-cp38-abi3-macosx_11_0_x86_64.whl", "cp310-macosx_x86_64"),
        ("foo-0.1-cp38-abi3-manylinux2014_x86_64.whl", "cp310-manylinux_x86_64"),
        ("foo-0.1-cp38-abi3-musllinux_1_1_x86_64.whl", "cp310-musllinux_x86_64"),
        ("foo-0.1-py2.py3-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py2.py3-none-win_amd64.whl", "pp310-win_amd64"),
        ("foo-0.1-py3-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "pp310-win_amd64"),
    ],
)
def test_find_compatible_wheel_found(wheel: str, identifier: str) -> None:
    wheel_ = PurePath(wheel)
    found = find_compatible_wheel([wheel_], identifier)
    assert found is wheel_


@pytest.mark.parametrize(
    ("wheel", "identifier"),
    [
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp310-win32"),
        ("foo-0.1-cp38-abi3-win_amd64.whl", "cp37-win_amd64"),
        ("foo-0.1-cp38-abi3-macosx_11_0_x86_64.whl", "cp310-macosx_universal2"),
        ("foo-0.1-cp38-abi3-manylinux2014_x86_64.whl", "cp310-musllinux_x86_64"),
        ("foo-0.1-cp38-abi3-musllinux_1_1_x86_64.whl", "cp310-manylinux_x86_64"),
        ("foo-0.1-py2-none-win_amd64.whl", "cp310-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "cp37-win_amd64"),
        ("foo-0.1-py38-none-win_amd64.whl", "pp37-win_amd64"),
        ("foo-0.1-cp38-cp38-win_amd64.whl", "cp310-win_amd64"),
    ],
)
def test_find_compatible_wheel_not_found(wheel: str, identifier: str) -> None:
    assert find_compatible_wheel([PurePath(wheel)], identifier) is None


def test_fix_ansi_codes_for_github_actions():
    input = textwrap.dedent(
        """
        This line is normal
        \033[1mThis line is bold
        This line is also bold
        \033[31m this line is red and bold
        This line is red and bold, too\033[0m
        This line is normal again
        """
    )

    expected = textwrap.dedent(
        """
        This line is normal
        \033[1mThis line is bold
        \033[1mThis line is also bold
        \033[1m\033[31m this line is red and bold
        \033[1m\033[31mThis line is red and bold, too\033[0m
        This line is normal again
        """
    )

    output = fix_ansi_codes_for_github_actions(input)

    assert output == expected


def test_parse_key_value_string():
    assert parse_key_value_string("bar", positional_arg_names=["foo"]) == {"foo": ["bar"]}
    assert parse_key_value_string("foo:bar", kw_arg_names=["foo"]) == {"foo": ["bar"]}
    with pytest.raises(ValueError, match="Too many positional arguments"):
        parse_key_value_string("bar")
    with pytest.raises(ValueError, match="Unknown field name"):
        parse_key_value_string("foo:bar")
    assert parse_key_value_string("foo:bar", kw_arg_names=["foo"]) == {"foo": ["bar"]}
    assert parse_key_value_string("foo:bar", positional_arg_names=["foo"]) == {"foo": ["bar"]}
    assert parse_key_value_string("foo: bar", kw_arg_names=["foo"]) == {"foo": ["bar"]}
    assert parse_key_value_string("foo: bar", kw_arg_names=["foo"]) == {"foo": ["bar"]}
    assert parse_key_value_string("foo: bar; baz: qux", kw_arg_names=["foo", "baz"]) == {
        "foo": ["bar"],
        "baz": ["qux"],
    }

    # some common options
    assert parse_key_value_string(
        "docker; create_args: --some-option --another-option=foo",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["--some-option", "--another-option=foo"],
    }
    # semicolon in value
    assert parse_key_value_string(
        "docker; create_args: --some-option='this; that'",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["--some-option=this; that"],
    }
    # colon in value
    assert parse_key_value_string(
        "docker; create_args: --mount a:b",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["--mount", "a:b"],
    }
    assert parse_key_value_string(
        "docker;create_args:--mount a:b",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["--mount", "a:b"],
    }
    # quoted value with spaces
    assert parse_key_value_string(
        "docker;create_args:'some string with spaces'",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["some string with spaces"],
    }

    # colon in positional value
    assert parse_key_value_string(
        "docker; --mount a:b",
        positional_arg_names=["name", "create_args"],
    ) == {
        "name": ["docker"],
        "create_args": ["--mount", "a:b"],
    }

    # empty option gives empty array
    assert parse_key_value_string(
        "docker;create_args:",
        positional_arg_names=["name"],
        kw_arg_names=["create_args"],
    ) == {
        "name": ["docker"],
        "create_args": [],
    }


def test_flexible_version_comparisons():
    assert FlexibleVersion("2.0") == FlexibleVersion("2")
    assert FlexibleVersion("2.0") < FlexibleVersion("2.1")
    assert FlexibleVersion("2.1") > FlexibleVersion("2")
    assert FlexibleVersion("1.9.9") < FlexibleVersion("2.0")
    assert FlexibleVersion("1.10") > FlexibleVersion("1.9.9")
    assert FlexibleVersion("3.0.1") > FlexibleVersion("3.0")
    assert FlexibleVersion("3.0") < FlexibleVersion("3.0.1")
    # Suffix should not affect comparisons
    assert FlexibleVersion("1.0.1-rhel") > FlexibleVersion("1.0")
    assert FlexibleVersion("1.0.1-rhel") < FlexibleVersion("1.1")
    assert FlexibleVersion("1.0.1") == FlexibleVersion("v1.0.1")


@pytest.fixture
def sample_project(tmp_path):
    """Create a directory structure that contains a range of files."""
    project_path = tmp_path / "project"

    (project_path / "src/deep").mkdir(parents=True)
    (project_path / "tests/deep").mkdir(parents=True)
    (project_path / "other").mkdir(parents=True)

    (project_path / "pyproject.toml").write_text("A pyproject.toml file")
    (project_path / "test.cfg").write_text("A test config file")

    (project_path / "src/__init__.py").write_text("source init")
    (project_path / "src/module.py").write_text("source module")
    (project_path / "src/deep/__init__.py").write_text("deep source init")

    (project_path / "tests/test_module.py").write_text("test module")
    (project_path / "tests/deep/test_module.py").write_text("deep test module")
    (project_path / "tests/deep/__init__.py").write_text("deep test init")

    (project_path / "other/module.py").write_text("other module")

    return project_path


@pytest.mark.parametrize(
    ("test_sources", "expected", "not_expected"),
    [
        # Empty test_sources copies nothing.
        pytest.param(
            [],
            [],
            [
                "pyproject.toml",
                "test.cfg",
                "other/module.py",
                "src/__init__.py",
                "src/module.py",
                "src/deep/__init__.py",
                "tests/test_module.py",
                "tests/deep/__init__.py",
                "tests/deep/test_module.py",
            ],
            id="empty",
        ),
        # Single standalone files
        pytest.param(
            ["pyproject.toml", "tests/deep/test_module.py"],
            ["pyproject.toml", "tests/deep/test_module.py"],
            [
                "test.cfg",
                "other/module.py",
                "src/__init__.py",
                "src/module.py",
                "src/deep/__init__.py",
                "tests/test_module.py",
                "tests/deep/__init__.py",
            ],
            id="single-file",
        ),
        # A full Directory
        pytest.param(
            ["tests"],
            [
                "tests/test_module.py",
                "tests/deep/__init__.py",
                "tests/deep/test_module.py",
            ],
            [
                "pyproject.toml",
                "test.cfg",
                "other/module.py",
                "src/__init__.py",
                "src/module.py",
                "src/deep/__init__.py",
            ],
            id="top-level-directory",
        ),
        # A partial deep directory
        pytest.param(
            ["tests/deep"],
            [
                "tests/deep/__init__.py",
                "tests/deep/test_module.py",
            ],
            [
                "pyproject.toml",
                "test.cfg",
                "other/module.py",
                "src/__init__.py",
                "src/module.py",
                "src/deep/__init__.py",
                "tests/test_module.py",
            ],
            id="partial-directory",
        ),
    ],
)
def test_copy_test_sources(tmp_path, sample_project, test_sources, expected, not_expected):
    """Test sources can be copied into the test directory."""
    target = tmp_path / "somewhere/test_cwd"
    copy_test_sources(test_sources, sample_project, target)

    for path in expected:
        assert (tmp_path / "somewhere/test_cwd" / path).is_file()

    for path in not_expected:
        assert not (tmp_path / "somewhere/test_cwd" / path).exists()


def test_copy_test_sources_missing_file(tmp_path, sample_project):
    """If test_sources references a folder that doesn't exist, an error is raised."""

    with pytest.raises(
        errors.FatalError,
        match=r"Test source tests/does_not_exist.py does not exist.",
    ):
        copy_test_sources(
            ["pyproject.toml", "tests/does_not_exist.py"],
            sample_project,
            tmp_path / "somewhere/test_cwd",
        )


def test_copy_test_sources_alternate_copy_into(sample_project):
    """If an alternate copy_into method is provided, it is used."""

    target = PurePath("/container/test_cwd")
    copy_into = Mock()

    copy_test_sources(["pyproject.toml", "tests"], sample_project, target, copy_into=copy_into)

    copy_into.assert_has_calls(
        [
            call(sample_project / "pyproject.toml", target / "pyproject.toml"),
            call(sample_project / "tests", target / "tests"),
        ],
        any_order=True,
    )


def test_unwrap():
    assert (
        unwrap("""
            This is a
            multiline
            string
        """)
        == "This is a multiline string"
    )


def test_unwrap_preserving_paragraphs():
    assert (
        unwrap("""
            This is a
            multiline
            string
        """)
        == "This is a multiline string"
    )
    assert (
        unwrap_preserving_paragraphs("""
            paragraph one

            paragraph two
        """)
        == "paragraph one\n\nparagraph two"
    )
