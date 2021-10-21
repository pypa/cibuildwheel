from cibuildwheel.util import prepare_command


def test_prepare_command():
    assert prepare_command("python -m {project}", project="project") == "python -m project"
    assert prepare_command("python -m {something}", project="project") == "python -m {something}"
    assert (
        prepare_command(
            "{a,b}{b:.2e}{{c}}{d%s}{e:3}{f[0]}", a=42, b=3.14159  # type:ignore[arg-type]
        )
        == "{a,b}3.14e+00{c}{d%s}{e:3}{f[0]}"
    )
