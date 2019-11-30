import sys
import os
import subprocess

import pytest

from cibuildwheel.__main__ import main
from cibuildwheel import windows, linux, macos
from cibuildwheel.util import BuildSelector
from cibuildwheel.environment import ParsedEnvironment

@pytest.fixture
def argtest():
    class TestArgs(object):
        def __call__(self, **kwargs): 
            self.kwargs = dict(kwargs)
    return TestArgs()

def not_call_mock(*args, **kwargs):
    raise RuntimeError("This should never be called")


def apply_mock_protection(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", not_call_mock)
    monkeypatch.setattr(windows, "urlopen", not_call_mock)
    monkeypatch.setattr(windows, "build", not_call_mock)
    monkeypatch.setattr(linux, "build", not_call_mock)
    monkeypatch.setattr(macos, "build", not_call_mock)
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    monkeypatch.setattr(sys, "argv", ["python", "abcabc"])


def test_unknown_platform_non_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {})
    apply_mock_protection(monkeypatch)
    with pytest.raises(SystemExit) as exit:
        main()
    assert exit.value.code == 2
    _, err = capsys.readouterr()
    assert 'cibuildwheel: Unable to detect platform.' in err
    assert "cibuildwheel should run on your CI server" in err


def test_unknown_platform_on_ci(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {"CI": "true"})
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(sys, "platform", "Something")

    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unable to detect platform from "sys.platform"' in err


def test_unknown_platform(monkeypatch, capsys):
    monkeypatch.setattr(os, 'environ', {"CIBW_PLATFORM": "Something"})
    apply_mock_protection(monkeypatch)
    with pytest.raises(SystemExit) as exit:
        main()
    _, err = capsys.readouterr()
    assert exit.value.code == 2
    assert 'cibuildwheel: Unsupported platform: Something' in err

@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("choose_platform_method", ["partameter", "environment"])
def test_platform_chose(system, choose_platform_method, argtest, monkeypatch):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    if choose_platform_method == "partameter":
        monkeypatch.setattr(sys, "argv", sys.argv + ["--platform", system])
    else:
        monkeypatch.setattr(os, 'environ', {"CIBW_PLATFORM": system})
    main()
    assert argtest.kwargs["project_dir"] == "abcabc"

@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("output_dir", ["partameter", "environment", "both", "none"])
def test_output_dir_set(system, output_dir, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    output_name = "out"
    env = {"CIBW_PLATFORM": system}
    if output_dir == "partameter":
        monkeypatch.setattr(sys, "argv", sys.argv + ["--output-dir", output_name])
    elif output_dir == "environment":
        env["CIBW_OUTPUT_DIR"] = output_name
    elif output_dir == "both":
        monkeypatch.setattr(sys, "argv", sys.argv + ["--output-dir", output_name])
        env["CIBW_OUTPUT_DIR"] = output_name + "aaa"
    else:
        output_name = "wheelhouse"
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert argtest.kwargs["output_dir"] == output_name

@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("build,build_set", [
    ("*", {"aaaa", "abcd", "abab", "bcde"}),
    ("a*", {"aaaa", "abcd", "abab"}),
    ("*b*", {"abcd", "abab", "bcde"})
    ])
@pytest.mark.parametrize("skip,skip_set", [
    ("", set()), ("a*", {"aaaa", "abcd", "abab"}),
    ("*c*", {"abcd", "bcde"})
])
def test_build_selector(system, build, build_set, skip, skip_set, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system, "CIBW_BUILD": build, "CIBW_SKIP": skip}
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert isinstance(argtest.kwargs["build_selector"], BuildSelector)
    selector = argtest.kwargs["build_selector"]
    selected = set([x for x in ["aaaa", "abcd", "abab", "bcde"] if selector(x)])
    assert selected == build_set.difference(skip_set)


@pytest.mark.parametrize("system", ["macos", "windows"])
@pytest.mark.parametrize("manylinux", ["none", "manylinux1"])
def test_no_manylinux(system, manylinux, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system}
    if manylinux != "none":
        env["CIBW_MANYLINUX_I686_IMAGE"] = manylinux
        env["CIBW_MANYLINUX_X86_64_IMAGE"] = manylinux
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert "manylinux_images" not in argtest.kwargs


@pytest.mark.parametrize("manylinux86,manylinux86_image", [
    ("none", 'quay.io/pypa/manylinux2010_i686'), 
    ("manylinux1", 'quay.io/pypa/manylinux1_i686'),
    ("manylinux2010", 'quay.io/pypa/manylinux2010_i686'),
    ("asfsgd", "asfsgd")])
@pytest.mark.parametrize("manylinux64, manylinux64_image", [
    ("none", 'quay.io/pypa/manylinux2010_x86_64'), 
    ("manylinux1", 'quay.io/pypa/manylinux1_x86_64'),
    ("manylinux2010", 'quay.io/pypa/manylinux2010_x86_64'),
    ("asfsgd", "asfsgd")])
def test_manylinux_choose(manylinux86, manylinux86_image, manylinux64,
        manylinux64_image, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(linux, "build", argtest)
    env = {"CIBW_PLATFORM": "linux"}
    if manylinux86 != "none":
        env["CIBW_MANYLINUX_I686_IMAGE"] = manylinux86
    if manylinux64 != "none":
        env["CIBW_MANYLINUX_X86_64_IMAGE"] = manylinux64
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert argtest.kwargs["manylinux_images"]['x86_64'] == manylinux64_image
    assert argtest.kwargs["manylinux_images"]['i686'] == manylinux86_image


@pytest.mark.parametrize("system,default_repair", [
    ("macos", "delocate"), ("linux", "auditwheel"),
    ("windows", "")])
@pytest.mark.parametrize("repair_command", ["none", "aaaa", "repair -w {dest_dir} {wheel}"])
@pytest.mark.parametrize("system_suffix", (True, False))
def test_repair_command(system, default_repair, repair_command, system_suffix, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system}
    if repair_command != "none":
        env["CIBW_REPAIR_WHEEL_COMMAND"] = repair_command
    if system_suffix:
        env["CIBW_REPAIR_WHEEL_COMMAND_" + system.upper()] = "abcabc"
    monkeypatch.setattr(os, 'environ', env)
    main()
    if system_suffix:
        assert argtest.kwargs["repair_command"] == "abcabc"
    elif repair_command == "none":
        if default_repair:
            assert argtest.kwargs["repair_command"].startswith(default_repair)
        else:
            assert len(argtest.kwargs["repair_command"]) == 0
    else:
        assert argtest.kwargs["repair_command"] == repair_command

@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("environment", [{}, {"AAA": "123"}, {"AA1": "124", "AA2": "124"}])
@pytest.mark.parametrize("platform_environment", [{}, {"BBB": "123"}, {"BB1": "123", "BB2": "127"}])
def test_environment(system, environment, platform_environment, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system}
    cibw_env = " ".join(["{}={}".format(k, v) for k, v in environment.items()])
    platform_env = " ".join(["{}={}".format(k, v) for k, v in platform_environment.items()])
    if cibw_env:
        env["CIBW_ENVIRONMENT"] = cibw_env
    if platform_env:
        env["CIBW_ENVIRONMENT_{}".format(system.upper())] = platform_env
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert isinstance(argtest.kwargs["environment"], ParsedEnvironment)
    if platform_environment:
        assert argtest.kwargs["environment"].as_dictionary({}) == platform_environment
    else:
        assert argtest.kwargs["environment"].as_dictionary({}) == environment


def identity(x):
    return x


def extras(x):
    if x is None:
        return ""
    return "[{}]".format(x)


def requires(x):
    if x is None:
        return []
    return x.split()


@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("generic_var", [None, "test1"])
@pytest.mark.parametrize("platform_generic_var", [None, "test2"])
@pytest.mark.parametrize("environ_var,kwargs_var,transform_var", [
    ("CIBW_BEFORE_BUILD", "before_build", identity), ("CIBW_TEST_COMMAND", "test_command", identity),
    ("CIBW_TEST_EXTRAS", "test_extras", extras), ("CIBW_TEST_REQUIRES", "test_requires", requires)])
def test_generic_var(system, generic_var, platform_generic_var, environ_var, kwargs_var, transform_var, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system}
    if generic_var:
        env[environ_var] = generic_var
    if platform_generic_var:
        env["{}_{}".format(environ_var, system.upper())] = platform_generic_var
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert isinstance(argtest.kwargs["environment"], ParsedEnvironment)
    if platform_generic_var:
        assert argtest.kwargs[kwargs_var] == transform_var(platform_generic_var)
    else:
        assert argtest.kwargs[kwargs_var] == transform_var(generic_var)


@pytest.mark.parametrize("system", ["macos", "linux", "windows"])
@pytest.mark.parametrize("verbosity", [None, 0, -2, 4])
@pytest.mark.parametrize("platform_verbosity", [None, 0, 2, -4])
def test_build_verbosity(system, verbosity, platform_verbosity, monkeypatch, argtest):
    apply_mock_protection(monkeypatch)
    monkeypatch.setattr(globals()[system], "build", argtest)
    env = {"CIBW_PLATFORM": system}
    if verbosity is not None:
        env["CIBW_BUILD_VERBOSITY"] = verbosity
    if platform_verbosity is not None:
        env["CIBW_BUILD_VERBOSITY_{}".format(system.upper())] = platform_verbosity
    monkeypatch.setattr(os, 'environ', env)
    main()
    assert isinstance(argtest.kwargs["environment"], ParsedEnvironment)
    if platform_verbosity is not None:
        assert argtest.kwargs["build_verbosity"] == platform_verbosity if platform_verbosity > -4 else -3
    elif verbosity is not None:
        assert argtest.kwargs["build_verbosity"] == verbosity if verbosity < 4 else 3
    else:
        assert argtest.kwargs["build_verbosity"] == 0