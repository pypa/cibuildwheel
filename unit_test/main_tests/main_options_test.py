from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from cibuildwheel.__main__ import main
from cibuildwheel.environment import ParsedEnvironment
from cibuildwheel.options import BuildOptions, _get_pinned_container_images
from cibuildwheel.util import BuildSelector, resources_dir, split_config_settings

# CIBW_PLATFORM is tested in main_platform_test.py


def test_output_dir(platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = Path("some_output_dir")

    monkeypatch.setenv("CIBW_OUTPUT_DIR", str(OUTPUT_DIR))

    main()

    assert intercepted_build_args.args[0].globals.output_dir == OUTPUT_DIR.resolve()


def test_output_dir_default(platform, intercepted_build_args, monkeypatch):
    main()

    assert intercepted_build_args.args[0].globals.output_dir == Path("wheelhouse").resolve()


@pytest.mark.parametrize("also_set_environment", [False, True])
def test_output_dir_argument(also_set_environment, platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = Path("some_output_dir")

    monkeypatch.setattr(sys, "argv", sys.argv + ["--output-dir", str(OUTPUT_DIR)])
    if also_set_environment:
        monkeypatch.setenv("CIBW_OUTPUT_DIR", "not_this_output_dir")

    main()

    assert intercepted_build_args.args[0].globals.output_dir == OUTPUT_DIR.resolve()


def test_build_selector(platform, intercepted_build_args, monkeypatch, allow_empty):
    BUILD = "some build* *-selector"
    SKIP = "some skip* *-selector"

    monkeypatch.setenv("CIBW_BUILD", BUILD)
    monkeypatch.setenv("CIBW_SKIP", SKIP)

    main()

    intercepted_build_selector = intercepted_build_args.args[0].globals.build_selector
    assert isinstance(intercepted_build_selector, BuildSelector)
    assert intercepted_build_selector("build24-this")
    assert not intercepted_build_selector("skip65-that")
    # This unit test is just testing the options of 'main'
    # Unit tests for BuildSelector are in build_selector_test.py


def test_empty_selector(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv("CIBW_SKIP", "*")

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 3


@pytest.mark.parametrize(
    "architecture, image, full_image",
    [
        ("x86_64", None, "quay.io/pypa/manylinux2014_x86_64:*"),
        ("x86_64", "manylinux1", "quay.io/pypa/manylinux1_x86_64:*"),
        ("x86_64", "manylinux2010", "quay.io/pypa/manylinux2010_x86_64:*"),
        ("x86_64", "manylinux2014", "quay.io/pypa/manylinux2014_x86_64:*"),
        ("x86_64", "manylinux_2_24", "quay.io/pypa/manylinux_2_24_x86_64:*"),
        ("x86_64", "manylinux_2_28", "quay.io/pypa/manylinux_2_28_x86_64:*"),
        ("x86_64", "custom_image", "custom_image"),
        ("i686", None, "quay.io/pypa/manylinux2014_i686:*"),
        ("i686", "manylinux1", "quay.io/pypa/manylinux1_i686:*"),
        ("i686", "manylinux2010", "quay.io/pypa/manylinux2010_i686:*"),
        ("i686", "manylinux2014", "quay.io/pypa/manylinux2014_i686:*"),
        ("i686", "manylinux_2_24", "quay.io/pypa/manylinux_2_24_i686:*"),
        ("i686", "custom_image", "custom_image"),
        ("pypy_x86_64", None, "quay.io/pypa/manylinux2014_x86_64:*"),
        ("pypy_x86_64", "manylinux1", "manylinux1"),  # Does not exist
        ("pypy_x86_64", "manylinux2010", "quay.io/pypa/manylinux2010_x86_64:*"),
        ("pypy_x86_64", "manylinux2014", "quay.io/pypa/manylinux2014_x86_64:*"),
        ("pypy_x86_64", "manylinux_2_24", "quay.io/pypa/manylinux_2_24_x86_64:*"),
        ("pypy_x86_64", "manylinux_2_28", "quay.io/pypa/manylinux_2_28_x86_64:*"),
        ("pypy_x86_64", "custom_image", "custom_image"),
    ],
)
def test_manylinux_images(
    architecture, image, full_image, platform, intercepted_build_args, monkeypatch
):
    if image is not None:
        monkeypatch.setenv("CIBW_MANYLINUX_" + architecture.upper() + "_IMAGE", image)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    if platform == "linux":
        assert fnmatch(
            build_options.manylinux_images[architecture],
            full_image,
        )
    else:
        assert build_options.manylinux_images is None


def get_default_repair_command(platform):
    if platform == "linux":
        return "auditwheel repair -w {dest_dir} {wheel}"
    elif platform == "macos":
        return "delocate-listdeps {wheel} && delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}"
    elif platform == "windows":
        return ""
    else:
        msg = f"Unknown platform: {platform!r}"
        raise ValueError(msg)


@pytest.mark.parametrize("repair_command", [None, "repair", "repair -w {dest_dir} {wheel}"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_repair_command(
    repair_command, platform_specific, platform, intercepted_build_args, monkeypatch
):
    if repair_command is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND_" + platform.upper(), repair_command)
            monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", "overwritten")
        else:
            monkeypatch.setenv("CIBW_REPAIR_WHEEL_COMMAND", repair_command)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    expected_repair = repair_command or get_default_repair_command(platform)
    assert build_options.repair_command == expected_repair


@pytest.mark.parametrize(
    "environment",
    [{}, {"something": "value"}, {"something": "value", "something_else": "other_value"}],
)
@pytest.mark.parametrize("platform_specific", [False, True])
def test_environment(environment, platform_specific, platform, intercepted_build_args, monkeypatch):
    env_string = " ".join(f"{k}={v}" for k, v in environment.items())
    if platform_specific:
        monkeypatch.setenv("CIBW_ENVIRONMENT_" + platform.upper(), env_string)
        monkeypatch.setenv("CIBW_ENVIRONMENT", "overwritten")
    else:
        monkeypatch.setenv("CIBW_ENVIRONMENT", env_string)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)
    intercepted_environment = build_options.environment

    assert isinstance(intercepted_environment, ParsedEnvironment)
    assert intercepted_environment.as_dictionary(prev_environment={}) == environment


@pytest.mark.parametrize("test_requires", [None, "requirement other_requirement"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_test_requires(
    test_requires, platform_specific, platform, intercepted_build_args, monkeypatch
):
    if test_requires is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_TEST_REQUIRES_" + platform.upper(), test_requires)
            monkeypatch.setenv("CIBW_TEST_REQUIRES", "overwritten")
        else:
            monkeypatch.setenv("CIBW_TEST_REQUIRES", test_requires)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    assert build_options.test_requires == (test_requires or "").split()


@pytest.mark.parametrize("test_extras", [None, "extras"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_test_extras(test_extras, platform_specific, platform, intercepted_build_args, monkeypatch):
    if test_extras is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_TEST_EXTRAS_" + platform.upper(), test_extras)
            monkeypatch.setenv("CIBW_TEST_EXTRAS", "overwritten")
        else:
            monkeypatch.setenv("CIBW_TEST_EXTRAS", test_extras)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    assert build_options.test_extras == ("[" + test_extras + "]" if test_extras else "")


@pytest.mark.parametrize("test_command", [None, "test --command"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_test_command(
    test_command, platform_specific, platform, intercepted_build_args, monkeypatch
):
    if test_command is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_TEST_COMMAND_" + platform.upper(), test_command)
            monkeypatch.setenv("CIBW_TEST_COMMAND", "overwritten")
        else:
            monkeypatch.setenv("CIBW_TEST_COMMAND", test_command)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    assert build_options.test_command == (test_command or "")


@pytest.mark.parametrize("before_build", [None, "before --build"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_before_build(
    before_build, platform_specific, platform, intercepted_build_args, monkeypatch
):
    if before_build is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_BEFORE_BUILD_" + platform.upper(), before_build)
            monkeypatch.setenv("CIBW_BEFORE_BUILD", "overwritten")
        else:
            monkeypatch.setenv("CIBW_BEFORE_BUILD", before_build)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)
    assert build_options.before_build == (before_build or "")


@pytest.mark.parametrize("build_verbosity", [None, 0, 2, -2, 4, -4])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_build_verbosity(
    build_verbosity, platform_specific, platform, intercepted_build_args, monkeypatch
):
    if build_verbosity is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_BUILD_VERBOSITY_" + platform.upper(), str(build_verbosity))
            monkeypatch.setenv("CIBW_BUILD_VERBOSITY", "overwritten")
        else:
            monkeypatch.setenv("CIBW_BUILD_VERBOSITY", str(build_verbosity))

    main()
    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    expected_verbosity = max(-3, min(3, int(build_verbosity or 0)))
    assert build_options.build_verbosity == expected_verbosity


@pytest.mark.parametrize("platform_specific", [False, True])
def test_config_settings(platform_specific, platform, intercepted_build_args, monkeypatch):
    config_settings = 'setting=value setting=value2 other="something else"'
    if platform_specific:
        monkeypatch.setenv("CIBW_CONFIG_SETTINGS_" + platform.upper(), config_settings)
        monkeypatch.setenv("CIBW_CONFIG_SETTIGNS", "a=b")
    else:
        monkeypatch.setenv("CIBW_CONFIG_SETTINGS", config_settings)

    main()
    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    assert build_options.config_settings == config_settings

    assert split_config_settings(config_settings) == [
        "--config-setting=setting=value",
        "--config-setting=setting=value2",
        "--config-setting=other=something else",
    ]


@pytest.mark.parametrize(
    "selector",
    [
        "CIBW_BUILD",
        "CIBW_SKIP",
        "CIBW_TEST_SKIP",
    ],
)
@pytest.mark.parametrize(
    "pattern",
    [
        "cp27-*",
        "cp35-*",
        "?p27*",
        "?p2*",
        "?p35*",
    ],
)
def test_build_selector_deprecated_error(
    monkeypatch, platform, intercepted_build_args, selector, pattern, allow_empty, capsys
):
    monkeypatch.setenv(selector, pattern)

    if selector == "CIBW_BUILD":
        with pytest.raises(SystemExit) as ex:
            main()
        assert ex.value.code == 4

    else:
        main()

    stderr = capsys.readouterr().err
    msg = f"cibuildwheel 2.x no longer supports Python < 3.6. Please use the 1.x series or update {selector}"
    assert msg in stderr


@pytest.mark.parametrize("before_all", ["", None, "test text"])
@pytest.mark.parametrize("platform_specific", [False, True])
def test_before_all(before_all, platform_specific, platform, intercepted_build_args, monkeypatch):
    if before_all is not None:
        if platform_specific:
            monkeypatch.setenv("CIBW_BEFORE_ALL_" + platform.upper(), before_all)
            monkeypatch.setenv("CIBW_BEFORE_ALL", "overwritten")
        else:
            monkeypatch.setenv("CIBW_BEFORE_ALL", before_all)

    main()

    build_options = intercepted_build_args.args[0].build_options(identifier=None)

    assert build_options.before_all == (before_all or "")


def test_defaults(platform, intercepted_build_args):
    main()

    build_options: BuildOptions = intercepted_build_args.args[0].build_options(identifier=None)
    defaults_config_path = resources_dir / "defaults.toml"
    with defaults_config_path.open("rb") as f:
        defaults_toml = tomllib.load(f)

    root_defaults = defaults_toml["tool"]["cibuildwheel"]
    platform_defaults = defaults_toml["tool"]["cibuildwheel"][platform]

    defaults = {}
    defaults.update(root_defaults)
    defaults.update(platform_defaults)

    # test a few options
    assert build_options.before_all == defaults["before-all"]
    repair_wheel_default = defaults["repair-wheel-command"]
    if isinstance(repair_wheel_default, list):
        repair_wheel_default = " && ".join(repair_wheel_default)
    assert build_options.repair_command == repair_wheel_default
    assert build_options.build_frontend == defaults["build-frontend"]

    if platform == "linux":
        assert build_options.manylinux_images
        pinned_images = _get_pinned_container_images()
        default_x86_64_image = pinned_images["x86_64"][defaults["manylinux-x86_64-image"]]
        assert build_options.manylinux_images["x86_64"] == default_x86_64_image
