import sys

import pytest

from cibuildwheel.__main__ import main
from cibuildwheel.architecture import Architecture

from .conftest import MOCK_PACKAGE_DIR


def test_unknown_platform_non_ci(monkeypatch, capsys):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("BITRISE_BUILD_NUMBER", raising=False)
    monkeypatch.delenv("AZURE_HTTP_USER_AGENT", raising=False)
    monkeypatch.delenv("TRAVIS", raising=False)
    monkeypatch.delenv("APPVEYOR", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    monkeypatch.delenv("CIRCLECI", raising=False)
    monkeypatch.delenv("CIBW_PLATFORM", raising=False)

    with pytest.raises(SystemExit) as exit:
        main()
        assert exit.value.code == 2
    _, err = capsys.readouterr()

    assert "cibuildwheel: Unable to detect platform." in err
    assert "cibuildwheel should run on your CI server" in err


def test_unknown_platform_on_ci(monkeypatch, capsys):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys, "platform", "nonexistent")
    monkeypatch.delenv("CIBW_PLATFORM", raising=False)

    with pytest.raises(SystemExit) as exit:
        main()
        assert exit.value.code == 2
    _, err = capsys.readouterr()

    assert 'cibuildwheel: Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch, capsys):
    monkeypatch.setenv("CIBW_PLATFORM", "nonexistent")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()

    assert exit.value.code == 2
    assert "cibuildwheel: Unsupported platform: nonexistent" in err


def test_platform_argument(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_PLATFORM", "nonexistent")
    monkeypatch.setattr(sys, "argv", sys.argv + ["--platform", platform])

    main()

    assert intercepted_build_args.args[0].package_dir == MOCK_PACKAGE_DIR


def test_platform_environment(platform, intercepted_build_args, monkeypatch):
    main()

    assert intercepted_build_args.args[0].package_dir == MOCK_PACKAGE_DIR


def test_archs_default(platform, intercepted_build_args, monkeypatch):

    main()
    build_options = intercepted_build_args.args[0]

    if platform == "linux":
        assert build_options.architectures == {Architecture.x86_64, Architecture.i686}
    elif platform == "windows":
        assert build_options.architectures == {Architecture.AMD64, Architecture.x86}
    else:
        assert build_options.architectures == {Architecture.x86_64}


@pytest.mark.parametrize("use_env_var", [False, True])
def test_archs_argument(platform, intercepted_build_args, monkeypatch, use_env_var):

    if use_env_var:
        monkeypatch.setenv("CIBW_ARCHS", "ppc64le")
    else:
        monkeypatch.setenv("CIBW_ARCHS", "unused")
        monkeypatch.setattr(sys, "argv", sys.argv + ["--archs", "ppc64le"])

    if platform in {"macos", "windows"}:
        with pytest.raises(SystemExit) as exit:
            main()
        assert exit.value.args == (4,)

    else:
        main()
        build_options = intercepted_build_args.args[0]
        assert build_options.architectures == {Architecture.ppc64le}


def test_archs_platform_specific(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "unused")
    monkeypatch.setenv("CIBW_ARCHS_LINUX", "ppc64le")
    monkeypatch.setenv("CIBW_ARCHS_WINDOWS", "x86")
    monkeypatch.setenv("CIBW_ARCHS_MACOS", "x86_64")

    main()
    build_options = intercepted_build_args.args[0]

    if platform == "linux":
        assert build_options.architectures == {Architecture.ppc64le}
    elif platform == "windows":
        assert build_options.architectures == {Architecture.x86}
    elif platform == "macos":
        assert build_options.architectures == {Architecture.x86_64}


def test_archs_platform_native(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "native")

    main()
    build_options = intercepted_build_args.args[0]

    if platform in {"linux", "macos"}:
        assert build_options.architectures == {Architecture.x86_64}
    elif platform == "windows":
        assert build_options.architectures == {Architecture.AMD64}


def test_archs_platform_auto64(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "auto64")

    main()
    build_options = intercepted_build_args.args[0]

    if platform in {"linux", "macos"}:
        assert build_options.architectures == {Architecture.x86_64}
    elif platform == "windows":
        assert build_options.architectures == {Architecture.AMD64}


def test_archs_platform_auto32(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "auto32")

    if platform == "macos":
        with pytest.raises(SystemExit) as exit:
            main()
        assert exit.value.args == (4,)

    else:
        main()

        build_options = intercepted_build_args.args[0]

        if platform == "linux":
            assert build_options.architectures == {Architecture.i686}
        elif platform == "windows":
            assert build_options.architectures == {Architecture.x86}


def test_archs_platform_all(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_ARCHS", "all")

    main()
    build_options = intercepted_build_args.args[0]

    if platform == "linux":
        assert build_options.architectures == {
            Architecture.x86_64,
            Architecture.i686,
            Architecture.aarch64,
            Architecture.ppc64le,
            Architecture.s390x,
        }
    elif platform == "windows":
        assert build_options.architectures == {Architecture.x86, Architecture.AMD64}
    elif platform == "macos":
        assert build_options.architectures == {
            Architecture.x86_64,
            Architecture.arm64,
            Architecture.universal2,
        }
