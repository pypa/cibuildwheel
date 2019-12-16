import pytest

import sys

from cibuildwheel.__main__ import main
from cibuildwheel.environment import ParsedEnvironment
from cibuildwheel.util import BuildSelector

from main_util_fixtures import mock_protection, platform, intercepted_build_args



# CIBW_PLATFORM is tested in main_platform_test.py


def test_output_dir(platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = 'some_output_dir'

    monkeypatch.setenv('CIBW_OUTPUT_DIR', OUTPUT_DIR)

    main()

    assert intercepted_build_args.kwargs['output_dir'] == OUTPUT_DIR


def test_output_dir_default(platform, intercepted_build_args, monkeypatch):
    main()

    assert intercepted_build_args.kwargs['output_dir'] == 'wheelhouse'


@pytest.mark.parametrize('also_set_environment', [False, True])
def test_output_dir_argument(also_set_environment, platform, intercepted_build_args, monkeypatch):
    OUTPUT_DIR = 'some_output_dir'

    monkeypatch.setattr(sys, 'argv', sys.argv + ['--output-dir', OUTPUT_DIR])
    if also_set_environment:
        monkeypatch.setenv('CIBW_OUTPUT_DIR', 'not_this_output_dir')

    main()

    assert intercepted_build_args.kwargs['output_dir'] == OUTPUT_DIR


def test_build_selector(platform, intercepted_build_args, monkeypatch):
    BUILD = 'some build* *-selector'
    SKIP = 'some skip* *-selector'

    monkeypatch.setenv('CIBW_BUILD', BUILD)
    monkeypatch.setenv('CIBW_SKIP', SKIP)

    main()
    
    intercepted_build_selector = intercepted_build_args.kwargs['build_selector']
    assert isinstance(intercepted_build_selector, BuildSelector)
    assert intercepted_build_selector('build-this')
    assert not intercepted_build_selector('skip-that')
    # This unit test is just testing the options of 'main'
    # Unit tests for BuildSelector are in build_selector_test.py


@pytest.mark.parametrize('architecture, image, full_image', [
    ('x86_64', None, 'quay.io/pypa/manylinux2010_x86_64'), 
    ('x86_64', 'manylinux1', 'quay.io/pypa/manylinux1_x86_64'),
    ('x86_64', 'manylinux2010', 'quay.io/pypa/manylinux2010_x86_64'),
    ('x86_64', 'custom_image', None),
    ('i686', None, 'quay.io/pypa/manylinux2010_i686'), 
    ('i686', 'manylinux1', 'quay.io/pypa/manylinux1_i686'),
    ('i686', 'manylinux2010', 'quay.io/pypa/manylinux2010_i686'),
    ('i686', 'custom_image', None),
])
def test_manylinux_images(architecture, image, full_image, platform, intercepted_build_args, monkeypatch):
    if image is not None:
        monkeypatch.setenv('CIBW_MANYLINUX_' + architecture.upper() + '_IMAGE', image)

    main()

    if platform == 'linux':
        assert intercepted_build_args.kwargs['manylinux_images'][architecture] == full_image or image
    else:
        assert 'manylinux_images' not in intercepted_build_args.kwargs


def get_default_repair_command(platform):
    if platform == 'linux':
        return 'auditwheel repair -w {dest_dir} {wheel}'
    elif platform == 'macos':
        return 'delocate-listdeps {wheel} && delocate-wheel -w {dest_dir} {wheel}'
    elif platform == 'windows':
        return ''

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
    assert intercepted_build_args.kwargs['repair_command'] == expected_repair


@pytest.mark.parametrize('environment', [
    {},
    {'something': 'value'},
    {'something': 'value', 'something_else': 'other_value'}
])
@pytest.mark.parametrize('platform_specific', [False, True])
def test_environment(environment, platform_specific, platform, intercepted_build_args, monkeypatch):
    env_string = ' '.join(['{}={}'.format(k, v) for k, v in environment.items()])
    if platform_specific:
        monkeypatch.setenv('CIBW_ENVIRONMENT_' + platform.upper(), env_string)
        monkeypatch.setenv('CIBW_ENVIRONMENT', 'overwritten')
    else:
        monkeypatch.setenv('CIBW_ENVIRONMENT', env_string)

    main()

    intercepted_environment = intercepted_build_args.kwargs['environment']
    assert isinstance(intercepted_environment, ParsedEnvironment)
    assert intercepted_environment.as_dictionary({}) == environment


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
    
    assert intercepted_build_args.kwargs['test_requires'] == (test_requires or '').split()


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
    
    assert intercepted_build_args.kwargs['test_extras'] == ('[' + test_extras + ']' if test_extras else '')


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

    assert intercepted_build_args.kwargs['test_command'] == test_command or ''


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

    assert intercepted_build_args.kwargs['before_build'] == before_build or ''


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
    assert intercepted_build_args.kwargs['build_verbosity'] == expected_verbosity
