from cibuildwheel.util import BuildSelector


def test_build():
    build_selector = BuildSelector(build_config="cp3?-* *-manylinux1*", skip_config="")

    assert build_selector('cp27-manylinux1_x86_64')
    assert build_selector('cp36-manylinux1_x86_64')
    assert build_selector('cp37-manylinux1_x86_64')
    assert build_selector('cp27-manylinux1_i686')
    assert build_selector('cp36-manylinux1_i686')
    assert build_selector('cp37-manylinux1_i686')
    assert not build_selector('cp27-macosx_10_6_intel')
    assert build_selector('cp36-macosx_10_6_intel')
    assert build_selector('cp37-macosx_10_6_intel')
    assert not build_selector('cp27-win32')
    assert build_selector('cp36-win32')
    assert build_selector('cp37-win32')
    assert not build_selector('cp27-win_amd64')
    assert build_selector('cp36-win_amd64')
    assert build_selector('cp37-win_amd64')


def test_skip():
    build_selector = BuildSelector(build_config="*", skip_config="cp27-* cp3?-manylinux1_i686 cp36-win* *-win32")

    assert not build_selector('cp27-manylinux1_x86_64')
    assert build_selector('cp36-manylinux1_x86_64')
    assert build_selector('cp37-manylinux1_x86_64')
    assert not build_selector('cp27-manylinux1_i686')
    assert not build_selector('cp36-manylinux1_i686')
    assert not build_selector('cp37-manylinux1_i686')
    assert not build_selector('cp27-macosx_10_6_intel')
    assert build_selector('cp36-macosx_10_6_intel')
    assert build_selector('cp37-macosx_10_6_intel')
    assert not build_selector('cp27-win32')
    assert not build_selector('cp36-win32')
    assert not build_selector('cp37-win32')
    assert not build_selector('cp27-win_amd64')
    assert not build_selector('cp36-win_amd64')
    assert build_selector('cp37-win_amd64')


def test_build_and_skip():
    build_selector = BuildSelector(build_config="cp36-* cp37-macosx* *-manylinux1*", skip_config="cp27-* cp37-manylinux1_i686")

    assert not build_selector('cp27-manylinux1_x86_64')
    assert build_selector('cp36-manylinux1_x86_64')
    assert build_selector('cp37-manylinux1_x86_64')
    assert not build_selector('cp27-manylinux1_i686')
    assert build_selector('cp36-manylinux1_i686')
    assert not build_selector('cp37-manylinux1_i686')
    assert not build_selector('cp27-macosx_10_6_intel')
    assert build_selector('cp36-macosx_10_6_intel')
    assert build_selector('cp37-macosx_10_6_intel')
    assert not build_selector('cp27-win32')
    assert build_selector('cp36-win32')
    assert not build_selector('cp37-win32')
    assert not build_selector('cp27-win_amd64')
    assert build_selector('cp36-win_amd64')
    assert not build_selector('cp37-win_amd64')


def test_build_braces():
    build_selector = BuildSelector(build_config="cp{36,37}*", skip_config="")

    assert not build_selector('cp27-manylinux1_x86_64')
    assert build_selector('cp36-manylinux1_x86_64')
    assert build_selector('cp37-manylinux1_x86_64')
    assert not build_selector('cp38-manylinux1_x86_64')
    assert not build_selector('cp39-manylinux1_x86_64')
