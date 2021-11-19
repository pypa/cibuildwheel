from cibuildwheel.util import format_safe, prepare_command


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
