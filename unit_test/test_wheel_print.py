import pytest

from cibuildwheel.util import print_new_wheels


def test_printout_wheels(tmp_path, capsys):
    tmp_path.joinpath("example.0").touch()
    with print_new_wheels("TEST_MSG: {n}", tmp_path):
        tmp_path.joinpath("example.1").touch()
        tmp_path.joinpath("example.2").touch()

    captured = capsys.readouterr()
    assert captured.err == ""

    assert "example.0" not in captured.out
    assert "example.1\n" in captured.out
    assert "example.2\n" in captured.out
    assert "TEST_MSG:" in captured.out
    assert "TEST_MSG: 2\n" in captured.out


def test_no_printout_on_error(tmp_path, capsys):
    tmp_path.joinpath("example.0").touch()
    with pytest.raises(RuntimeError):
        with print_new_wheels("TEST_MSG: {n}", tmp_path):
            tmp_path.joinpath("example.1").touch()
            raise RuntimeError()

    captured = capsys.readouterr()
    assert captured.err == ""

    assert "example.0" not in captured.out
    assert "example.1" not in captured.out
    assert "example.2" not in captured.out
    assert "TEST_MSG:" not in captured.out
