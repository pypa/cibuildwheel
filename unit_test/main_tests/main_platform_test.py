import sys

import pytest

from cibuildwheel.__main__ import main
from cibuildwheel.architecture import Architecture
from cibuildwheel.selector import EnableGroup

from ..conftest import MOCK_PACKAGE_DIR


@pytest.mark.parametrize("option_value", [None, "auto", ""])
def test_platform_unset_or_auto(monkeypatch, intercepted_build_args, option_value):
    if option_value is None:
        monkeypatch.delenv("CIBW_PLATFORM", raising=False)
    else:
        monkeypatch.setenv("CIBW_PLATFORM", option_value)

    main()

    options = intercepted_build_args.args[0]

    # check that the platform was auto detected to build for the current system
    if sys.platform.startswith("linux"):
        assert options.platform == "linux"
    elif sys.platform == "darwin":
        assert options.platform == "macos"
    elif sys.platform == "win32":
        assert options.platform == "windows"
    else:
        pytest.fail(f"Unknown platform: {sys.platform}")


def test_unknown_platform_on_ci(monkeypatch, capsys):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys, "platform", "nonexistent")
    monkeypatch.delenv("CIBW_PLATFORM", raising=False)

    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 2
    _, err = capsys.readouterr()

    assert 'Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch, capsys):
    monkeypatch.setenv("CIBW_PLATFORM", "nonexistent")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()

    assert exit.value.code == 2
    assert "Unsupported platform: nonexistent" in err


def test_platform_argument(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_PLATFORM", "nonexistent")
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--platform", platform])

    main()

    options = intercepted_build_args.args[0]

    assert options.globals.package_dir == MOCK_PACKAGE_DIR.resolve()


@pytest.mark.usefixtures("platform")
def test_platform_environment(intercepted_build_args):
    main()
    options = intercepted_build_args.args[0]

    assert options.globals.package_dir == MOCK_PACKAGE_DIR.resolve()


def test_archs_default(platform, intercepted_build_args):
    main()
    options = intercepted_build_args.args[0]

    if platform == "linux":
        assert options.globals.architectures == {Architecture.x86_64, Architecture.i686}
    elif platform == "windows":
        assert options.globals.architectures == {Architecture.AMD64, Architecture.x86}
    else:
        assert options.globals.architectures == {Architecture.x86_64}


@pytest.mark.parametrize("use_env_var", [False, True])
def test_archs_argument(platform, intercepted_build_args, monkeypatch, use_env_var):
    if use_env_var:
        monkeypatch.setenv("CIBW_ARCHS", "ppc64le")
    else:
        monkeypatch.setenv("CIBW_ARCHS", "unused")
        monkeypatch.setattr(sys, "argv", [*sys.argv, "--archs", "ppc64le"])

    if platform in {"macos", "windows"}:
        with pytest.raises(SystemExit) as exit:
            main()
        assert exit.value.args == (4,)

    else:
        main()
        options = intercepted_build_args.args[0]
        assert options.globals.architectures == {Architecture.ppc64le}


def test_archs_platform_specific(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "unused")
    monkeypatch.setenv("CIBW_ARCHS_LINUX", "ppc64le")
    monkeypatch.setenv("CIBW_ARCHS_WINDOWS", "x86")
    monkeypatch.setenv("CIBW_ARCHS_MACOS", "x86_64")

    main()
    options = intercepted_build_args.args[0]

    if platform == "linux":
        assert options.globals.architectures == {Architecture.ppc64le}
    elif platform == "windows":
        assert options.globals.architectures == {Architecture.x86}
    elif platform == "macos":
        assert options.globals.architectures == {Architecture.x86_64}


def test_archs_platform_native(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "native")

    main()
    options = intercepted_build_args.args[0]

    if platform in {"linux", "macos"}:
        assert options.globals.architectures == {Architecture.x86_64}
    elif platform == "windows":
        assert options.globals.architectures == {Architecture.AMD64}


def test_archs_platform_auto64(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "auto64")

    main()
    options = intercepted_build_args.args[0]

    if platform in {"linux", "macos"}:
        assert options.globals.architectures == {Architecture.x86_64}
    elif platform == "windows":
        assert options.globals.architectures == {Architecture.AMD64}


def test_archs_platform_auto32(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "auto32")

    if platform == "macos":
        with pytest.raises(SystemExit) as exit:
            main()
        assert exit.value.args == (4,)

    else:
        main()

        options = intercepted_build_args.args[0]

        if platform == "linux":
            assert options.globals.architectures == {Architecture.i686}
        elif platform == "windows":
            assert options.globals.architectures == {Architecture.x86}


def test_archs_platform_all(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "all")

    main()
    options = intercepted_build_args.args[0]

    if platform == "linux":
        assert options.globals.architectures == {
            Architecture.x86_64,
            Architecture.i686,
            Architecture.aarch64,
            Architecture.ppc64le,
            Architecture.s390x,
            Architecture.armv7l,
            Architecture.riscv64,
        }
    elif platform == "windows":
        assert options.globals.architectures == {
            Architecture.x86,
            Architecture.AMD64,
            Architecture.ARM64,
        }
    elif platform == "macos":
        assert options.globals.architectures == {
            Architecture.x86_64,
            Architecture.arm64,
            Architecture.universal2,
        }


@pytest.mark.parametrize(
    ("only", "plat"),
    (
        ("cp311-manylinux_x86_64", "linux"),
        ("cp310-win_amd64", "windows"),
        ("cp310-win32", "windows"),
        ("cp311-macosx_x86_64", "macos"),
    ),
)
def test_only_argument(intercepted_build_args, monkeypatch, only, plat):
    monkeypatch.setenv("CIBW_BUILD", "unused")
    monkeypatch.setenv("CIBW_SKIP", "unused")
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--only", only])

    main()

    options = intercepted_build_args.args[0]
    assert options.globals.build_selector.build_config == only
    assert options.globals.build_selector.skip_config == ""
    assert options.platform == plat
    assert options.globals.architectures == Architecture.all_archs(plat)
    assert EnableGroup.PyPy in options.globals.build_selector.enable


@pytest.mark.parametrize("only", ("cp311-manylxinux_x86_64", "some_linux_thing"))
def test_only_failed(monkeypatch, only):
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--only", only])

    with pytest.raises(SystemExit):
        main()


def test_only_no_platform(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", [*sys.argv, "--only", "cp311-manylinux_x86_64", "--platform", "macos"]
    )

    with pytest.raises(SystemExit):
        main()


def test_only_no_archs(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", [*sys.argv, "--only", "cp311-manylinux_x86_64", "--archs", "x86_64"]
    )

    with pytest.raises(SystemExit):
        main()


@pytest.mark.parametrize(
    ("envvar_name", "envvar_value"),
    (
        ("CIBW_BUILD", "cp310-*"),
        ("CIBW_SKIP", "cp311-*"),
        ("CIBW_ARCHS", "auto32"),
        ("CIBW_PLATFORM", "macos"),
    ),
)
def test_only_overrides_env_vars(monkeypatch, intercepted_build_args, envvar_name, envvar_value):
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--only", "cp311-manylinux_x86_64"])
    monkeypatch.setenv(envvar_name, envvar_value)

    main()

    options = intercepted_build_args.args[0]
    assert options.globals.build_selector.build_config == "cp311-manylinux_x86_64"
    assert options.globals.build_selector.skip_config == ""
    assert options.platform == "linux"
    assert options.globals.architectures == Architecture.all_archs("linux")


def test_pyodide_on_windows(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--only", "cp312-pyodide_wasm32"])

    with pytest.raises(SystemExit) as exit:
        main()

    _, err = capsys.readouterr()

    assert exit.value.code == 2
    assert "Building for pyodide is not supported on Windows" in err
