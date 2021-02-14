import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest

from cibuildwheel.__main__ import main
from cibuildwheel.environment import ParsedEnvironment
from cibuildwheel.util import BuildSelector

# CIBW_PLATFORM is tested in main_platform_test.py


def test_output_dir(platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = Path('some_output_dir')

    monkeypatch.setenv('CIBW_OUTPUT_DIR', str(OUTPUT_DIR))

    main()

    assert intercepted_build_args.args[0].output_dir == OUTPUT_DIR


def test_output_dir_default(platform, intercepted_build_args, monkeypatch):
    main()

    assert intercepted_build_args.args[0].output_dir == Path('wheelhouse')


@pytest.mark.parametrize('also_set_environment', [False, True])
def test_output_dir_argument(also_set_environment, platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = Path('some_output_dir')

    monkeypatch.setattr(sys, 'argv', sys.argv + ['--output-dir', str(OUTPUT_DIR)])
    if also_set_environment:
        monkeypatch.setenv('CIBW_OUTPUT_DIR', 'not_this_output_dir')

    main()

    assert intercepted_build_args.args[0].output_dir == OUTPUT_DIR


def test_build_selector(platform, intercepted_build_args, monkeypatch, allow_empty):
    BUILD = 'some build* *-selector'
    SKIP = 'some skip* *-selector'

    monkeypatch.setenv('CIBW_BUILD', BUILD)
    monkeypatch.setenv('CIBW_SKIP', SKIP)

    main()

    intercepted_build_selector = intercepted_build_args.args[0].build_selector
    assert isinstance(intercepted_build_selector, BuildSelector)
    assert intercepted_build_selector('build24-this')
    assert not intercepted_build_selector('skip65-that')
    # This unit test is just testing the options of 'main'
    # Unit tests for BuildSelector are in build_selector_test.py


def test_empty_selector(platform, intercepted_build_args, monkeypatch):
    monkeypatch.setenv('CIBW_SKIP', '*')

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 3


@pytest.mark.parametrize('architecture, image, full_image', [
    ('x86_64', None, 'quay.io/pypa/manylinux2010_x86_64:*'),
    ('x86_64', 'manylinux1', 'quay.io/pypa/manylinux1_x86_64:*'),
    ('x86_64', 'manylinux2010', 'quay.io/pypa/manylinux2010_x86_64:*'),
    ('x86_64', 'manylinux2014', 'quay.io/pypa/manylinux2014_x86_64:*'),
    ('x86_64', 'manylinux_2_24', 'quay.io/pypa/manylinux_2_24_x86_64:*'),
    ('x86_64', 'custom_image', 'custom_image'),
    ('i686', None, 'quay.io/pypa/manylinux2010_i686:*'),
    ('i686', 'manylinux1', 'quay.io/pypa/manylinux1_i686:*'),
    ('i686', 'manylinux2010', 'quay.io/pypa/manylinux2010_i686:*'),
    ('i686', 'manylinux2014', 'quay.io/pypa/manylinux2014_i686:*'),
    ('i686', 'manylinux_2_24', 'quay.io/pypa/manylinux_2_24_i686:*'),
    ('i686', 'custom_image', 'custom_image'),
    ('pypy_x86_64', None, 'pypywheels/manylinux2010-pypy_x86_64:*'),
    ('pypy_x86_64', 'manylinux1', 'manylinux1'),  # Does not exist
    ('pypy_x86_64', 'manylinux2010', 'pypywheels/manylinux2010-pypy_x86_64:*'),
    ('pypy_x86_64', 'manylinux2014', 'manylinux2014'),  # Does not exist (yet)
    ('pypy_x86_64', 'custom_image', 'custom_image'),
])
def test_manylinux_images(architecture, image, full_image, platform, intercepted_build_args, monkeypatch):
    if image is not None:
        monkeypatch.setenv('CIBW_MANYLINUX_' + architecture.upper() + '_IMAGE', image)

    main()

    if platform == 'linux':
        assert fnmatch(
            intercepted_build_args.args[0].manylinux_images[architecture],
            full_image
        )
    else:
        assert intercepted_build_args.args[0].manylinux_images is None


def get_default_repair_command(platform):
    if platform == 'linux':
        return 'auditwheel repair -w {dest_dir} {wheel}'
    elif platform == 'macos':
        return 'delocate-listdeps {wheel} && delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}'
    elif platform == 'windows':
        return ''
    else:
        raise ValueError('Unknown platform', platform)


@pytest.mark.parametrize('repair_command', [None, 'repair', 'repair -w {dest_dir} {wheel}'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_repair_command(repair_command, platform_specific, platform, intercepted_build_args, monkeypatch):
    if repair_command is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_REPAIR_WHEEL_COMMAND_' + platform.upper(), repair_command)
            monkeypatch.setenv('CIBW_REPAIR_WHEEL_COMMAND', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_REPAIR_WHEEL_COMMAND', repair_command)

    main()

    expected_repair = repair_command or get_default_repair_command(platform)
    assert intercepted_build_args.args[0].repair_command == expected_repair


@pytest.mark.parametrize('environment', [
    {},
    {'something': 'value'},
    {'something': 'value', 'something_else': 'other_value'}
])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_environment(environment, platform_specific, platform, intercepted_build_args, monkeypatch):
    env_string = ' '.join([f'{k}={v}' for k, v in environment.items()])
    if platform_specific:
        monkeypatch.setenv('CIBW_ENVIRONMENT_' + platform.upper(), env_string)
        monkeypatch.setenv('CIBW_ENVIRONMENT', 'overwritten')
    else:
        monkeypatch.setenv('CIBW_ENVIRONMENT', env_string)

    main()

    intercepted_environment = intercepted_build_args.args[0].environment
    assert isinstance(intercepted_environment, ParsedEnvironment)
    assert intercepted_environment.as_dictionary(prev_environment={}) == environment


@pytest.mark.parametrize('test_requires', [None, 'requirement other_requirement'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_test_requires(test_requires, platform_specific, platform, intercepted_build_args, monkeypatch):
    if test_requires is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_TEST_REQUIRES_' + platform.upper(), test_requires)
            monkeypatch.setenv('CIBW_TEST_REQUIRES', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_TEST_REQUIRES', test_requires)

    main()

    assert intercepted_build_args.args[0].test_requires == (test_requires or '').split()


@pytest.mark.parametrize('test_extras', [None, 'extras'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_test_extras(test_extras, platform_specific, platform, intercepted_build_args, monkeypatch):
    if test_extras is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_TEST_EXTRAS_' + platform.upper(), test_extras)
            monkeypatch.setenv('CIBW_TEST_EXTRAS', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_TEST_EXTRAS', test_extras)

    main()

    assert intercepted_build_args.args[0].test_extras == ('[' + test_extras + ']' if test_extras else '')


@pytest.mark.parametrize('test_command', [None, 'test --command'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_test_command(test_command, platform_specific, platform, intercepted_build_args, monkeypatch):
    if test_command is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_TEST_COMMAND_' + platform.upper(), test_command)
            monkeypatch.setenv('CIBW_TEST_COMMAND', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_TEST_COMMAND', test_command)

    main()

    assert intercepted_build_args.args[0].test_command == test_command


@pytest.mark.parametrize('before_build', [None, 'before --build'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_before_build(before_build, platform_specific, platform, intercepted_build_args, monkeypatch):
    if before_build is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_BEFORE_BUILD_' + platform.upper(), before_build)
            monkeypatch.setenv('CIBW_BEFORE_BUILD', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_BEFORE_BUILD', before_build)

    main()

    assert intercepted_build_args.args[0].before_build == before_build


@pytest.mark.parametrize('build_verbosity', [None, 0, 2, -2, 4, -4])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_build_verbosity(build_verbosity, platform_specific, platform, intercepted_build_args, monkeypatch):
    if build_verbosity is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_BUILD_VERBOSITY_' + platform.upper(), str(build_verbosity))
            monkeypatch.setenv('CIBW_BUILD_VERBOSITY', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_BUILD_VERBOSITY', str(build_verbosity))

    main()

    expected_verbosity = max(-3, min(3, int(build_verbosity or 0)))
    assert intercepted_build_args.args[0].build_verbosity == expected_verbosity


@pytest.mark.parametrize('option_name', ['CIBW_BUILD', 'CIBW_SKIP'])
@pytest.mark.parametrize('option_value, build_selector_patterns', [
    ('*-manylinux1_*', ['*-manylinux_*']),
    ('*-macosx_10_6_intel', ['*-macosx_x86_64']),
    ('*-macosx_10_9_x86_64', ['*-macosx_x86_64']),
    ('cp37-macosx_10_9_x86_64', ['cp37-macosx_x86_64']),
])
def test_build_selector_migrations(intercepted_build_args, monkeypatch, option_name, option_value, build_selector_patterns, allow_empty):
    monkeypatch.setenv(option_name, option_value)

    main()

    intercepted_build_selector = intercepted_build_args.args[0].build_selector
    assert isinstance(intercepted_build_selector, BuildSelector)

    if option_name == 'CIBW_BUILD':
        assert intercepted_build_selector.build_patterns == build_selector_patterns
    else:
        assert intercepted_build_selector.skip_patterns == build_selector_patterns


@pytest.mark.parametrize('before_all', ["", None, 'test text'])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_before_all(before_all, platform_specific, platform, intercepted_build_args, monkeypatch):
    if before_all is not None:
        if platform_specific:
            monkeypatch.setenv('CIBW_BEFORE_ALL_' + platform.upper(), before_all)
            monkeypatch.setenv('CIBW_BEFORE_ALL', 'overwritten')
        else:
            monkeypatch.setenv('CIBW_BEFORE_ALL', before_all)

    main()

    if before_all is None:
        before_all = ""

    assert intercepted_build_args.args[0].before_all == before_all
