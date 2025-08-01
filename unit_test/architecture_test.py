import platform as platform_module
import shutil
import sys

import pytest

import cibuildwheel.architecture
from cibuildwheel.architecture import Architecture, arch_synonym


@pytest.fixture(
    params=[
        pytest.param(("linux", "linux", "x86_64", "64"), id="linux-64"),
        pytest.param(("linux", "linux", "i686", "32"), id="linux-32"),
        pytest.param(("linux", "linux", "aarch64", "arm"), id="linux-arm"),
        pytest.param(("macos", "darwin", "x86_64", "64"), id="macos-64"),
        pytest.param(("macos", "darwin", "arm64", "arm"), id="macos-arm"),
        pytest.param(("windows", "win32", "x86", "32"), id="windows-32"),
        pytest.param(("windows", "win32", "AMD64", "64"), id="windows-64"),
        pytest.param(("windows", "win32", "ARM64", "arm"), id="windows-arm"),
    ]
)
def platform_machine(request, monkeypatch):
    platform_name, platform_value, machine_value, machine_name = request.param
    monkeypatch.setattr(sys, "platform", platform_value)
    monkeypatch.setattr(platform_module, "machine", lambda: machine_value)
    monkeypatch.setattr(cibuildwheel.architecture, "_check_aarch32_el0", lambda: True)
    return platform_name, machine_name


def test_arch_auto(platform_machine):
    _, machine_name = platform_machine

    arch_set = Architecture.auto_archs("linux")
    expected = {
        "32": {Architecture.i686},
        "64": {Architecture.x86_64},
        "arm": {Architecture.aarch64},
    }
    assert arch_set == expected[machine_name]

    arch_set = Architecture.auto_archs("macos")
    expected = {"32": set(), "64": {Architecture.x86_64}, "arm": {Architecture.arm64}}
    assert arch_set == expected[machine_name]

    arch_set = Architecture.auto_archs("windows")
    expected = {
        "32": {Architecture.x86},
        "64": {Architecture.AMD64, Architecture.x86},
        "arm": {Architecture.ARM64},
    }
    assert arch_set == expected[machine_name]


def test_arch_auto64(platform_machine):
    _, machine_name = platform_machine

    arch_set = Architecture.parse_config("auto64", "linux")
    expected = {"32": set(), "64": {Architecture.x86_64}, "arm": {Architecture.aarch64}}
    assert arch_set == expected[machine_name]

    arch_set = Architecture.parse_config("auto64", "macos")
    expected = {"32": set(), "64": {Architecture.x86_64}, "arm": {Architecture.arm64}}
    assert arch_set == expected[machine_name]

    arch_set = Architecture.parse_config("auto64", "windows")
    expected = {"32": set(), "64": {Architecture.AMD64}, "arm": {Architecture.ARM64}}
    assert arch_set == expected[machine_name]


def test_arch_auto32(platform_machine):
    _, machine_name = platform_machine

    arch_set = Architecture.parse_config("auto32", "linux")
    expected = {"32": {Architecture.i686}, "64": {Architecture.i686}, "arm": {Architecture.armv7l}}
    assert arch_set == expected[machine_name]

    arch_set = Architecture.parse_config("auto32", "macos")
    assert arch_set == set()

    arch_set = Architecture.parse_config("auto32", "windows")
    expected = {"32": {Architecture.x86}, "64": {Architecture.x86}, "arm": set()}
    assert arch_set == expected[machine_name]


def test_arch_auto_no_aarch32(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform_module, "machine", lambda: "aarch64")
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)

    arch_set = Architecture.parse_config("auto", "linux")
    assert arch_set == {Architecture.aarch64}

    arch_set = Architecture.parse_config("auto64", "linux")
    assert arch_set == {Architecture.aarch64}

    monkeypatch.setattr(cibuildwheel.architecture, "_check_aarch32_el0", lambda: True)
    arch_set = Architecture.parse_config("auto32", "linux")
    assert arch_set == {Architecture.armv7l}

    monkeypatch.setattr(cibuildwheel.architecture, "_check_aarch32_el0", lambda: False)
    arch_set = Architecture.parse_config("auto32", "linux")
    assert arch_set == set()


def test_arch_native_on_ios(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform_module, "machine", lambda: "arm64")
    arch_set = Architecture.parse_config("native", platform="ios")
    assert arch_set == {Architecture.arm64_iphonesimulator}


def test_arch_auto_on_ios(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform_module, "machine", lambda: "arm64")
    arch_set = Architecture.parse_config("auto", platform="ios")
    assert arch_set == {Architecture.arm64_iphonesimulator, Architecture.arm64_iphoneos}


@pytest.mark.parametrize(
    ("arch", "from_platform", "to_platform", "expected"),
    [
        ("x86_64", "linux", "macos", "x86_64"),
        ("x86_64", "macos", "linux", "x86_64"),
        ("x86_64", "linux", "windows", "AMD64"),
        ("AMD64", "windows", "linux", "x86_64"),
        ("x86_64", "linux", "nonexistent", "x86_64"),
        ("x86_64", "nonexistent", "linux", "x86_64"),
        ("nonexistent", "linux", "windows", "nonexistent"),
        ("x86", "windows", "macos", None),
    ],
)
def test_arch_synonym(arch, from_platform, to_platform, expected):
    assert arch_synonym(arch, from_platform, to_platform) == expected
