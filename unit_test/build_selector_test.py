import pytest
from packaging.specifiers import SpecifierSet

from cibuildwheel.util import BuildSelector


def test_build():
    build_selector = BuildSelector(build_config="cp3*-* *-manylinux*", skip_config="")

    assert build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
    assert build_selector("cp310-manylinux_x86_64")
    assert build_selector("pp36-manylinux_x86_64")
    assert build_selector("pp37-manylinux_x86_64")
    assert build_selector("cp36-manylinux_i686")
    assert build_selector("cp37-manylinux_i686")
    assert build_selector("cp36-macosx_intel")
    assert build_selector("cp37-macosx_intel")
    assert build_selector("cp39-macosx_intel")
    assert build_selector("cp39-macosx_universal2")
    assert build_selector("cp39-macosx_arm64")
    assert not build_selector("pp36-macosx_intel")
    assert not build_selector("pp37-macosx_intel")
    assert build_selector("cp36-win32")
    assert build_selector("cp37-win32")
    assert not build_selector("pp36-win32")
    assert not build_selector("pp37-win32")
    assert build_selector("cp36-win_amd64")
    assert build_selector("cp37-win_amd64")
    assert build_selector("cp310-win_amd64")
    assert not build_selector("pp36-win_amd64")
    assert not build_selector("pp37-win_amd64")


@pytest.mark.skip("this test only makes sense when we have a prerelease python to test with")
def test_build_filter_pre():
    build_selector = BuildSelector(
        build_config="cp3*-* *-manylinux*",
        skip_config="",
        prerelease_pythons=True,
    )

    assert build_selector("cp37-manylinux_x86_64")
    assert build_selector("cp310-manylinux_x86_64")
    assert build_selector("cp37-win_amd64")
    assert build_selector("cp310-win_amd64")


def test_skip():
    build_selector = BuildSelector(
        build_config="*", skip_config="pp36-* cp3?-manylinux_i686 cp36-win* *-win32"
    )

    assert not build_selector("pp36-manylinux_x86_64")
    assert build_selector("pp37-manylinux_x86_64")
    assert build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
    assert not build_selector("cp36-manylinux_i686")
    assert not build_selector("cp37-manylinux_i686")
    assert not build_selector("pp36-macosx_10_6_intel")
    assert build_selector("pp37-macosx_10_6_intel")
    assert build_selector("cp36-macosx_10_6_intel")
    assert build_selector("cp37-macosx_10_6_intel")
    assert not build_selector("cp36-win32")
    assert not build_selector("cp37-win32")
    assert not build_selector("cp36-win_amd64")
    assert build_selector("cp37-win_amd64")


def test_build_and_skip():
    build_selector = BuildSelector(
        build_config="cp36-* cp37-macosx* *-manylinux*", skip_config="pp37-* cp37-manylinux_i686"
    )

    assert not build_selector("pp37-manylinux_x86_64")
    assert build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
    assert not build_selector("pp37-manylinux_i686")
    assert build_selector("cp36-manylinux_i686")
    assert not build_selector("cp37-manylinux_i686")
    assert not build_selector("pp37-macosx_10_6_intel")
    assert build_selector("cp36-macosx_10_6_intel")
    assert build_selector("cp37-macosx_10_6_intel")
    assert not build_selector("pp37-win32")
    assert build_selector("cp36-win32")
    assert not build_selector("cp37-win32")
    assert not build_selector("pp37-win_amd64")
    assert build_selector("cp36-win_amd64")
    assert not build_selector("cp37-win_amd64")


def test_build_braces():
    build_selector = BuildSelector(build_config="cp{36,37}*", skip_config="")

    assert build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
    assert not build_selector("cp38-manylinux_x86_64")
    assert not build_selector("cp39-manylinux_x86_64")


def test_build_limited_python():
    build_selector = BuildSelector(
        build_config="*", skip_config="", requires_python=SpecifierSet(">=3.7")
    )

    assert not build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
    assert build_selector("cp38-manylinux_x86_64")
    assert not build_selector("cp36-manylinux_i686")
    assert build_selector("cp37-manylinux_i686")
    assert build_selector("cp38-manylinux_i686")
    assert not build_selector("cp36-win32")
    assert build_selector("cp37-win32")
    assert build_selector("cp38-win32")
    assert build_selector("pp37-win_amd64")


def test_build_limited_python_partial():
    build_selector = BuildSelector(
        build_config="*", skip_config="", requires_python=SpecifierSet(">=3.6, !=3.7.*")
    )

    assert build_selector("cp36-manylinux_x86_64")
    assert not build_selector("cp37-manylinux_x86_64")
    assert build_selector("cp38-manylinux_x86_64")
    assert build_selector("cp39-manylinux_x86_64")


def test_build_limited_python_patch():
    build_selector = BuildSelector(
        build_config="*", skip_config="", requires_python=SpecifierSet(">=3.6.8")
    )

    assert build_selector("cp36-manylinux_x86_64")
    assert build_selector("cp37-manylinux_x86_64")
