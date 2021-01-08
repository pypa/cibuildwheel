import re
import textwrap

import pytest

import cibuildwheel.util

from . import test_projects, utils

project_with_expected_version_checks = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(r'''
        import subprocess
        import os

        versions_output_text = subprocess.check_output(
            ['pip', 'freeze', '--all', '-qq'],
            universal_newlines=True,
        )
        versions = versions_output_text.strip().splitlines()

        # `versions` now looks like:
        # ['pip==x.x.x', 'setuptools==x.x.x', 'wheel==x.x.x']

        print('Gathered versions', versions)

        for package_name in ['pip', 'setuptools', 'wheel']:
            env_name = 'EXPECTED_{}_VERSION'.format(package_name.upper())
            expected_version = os.environ[env_name]

            assert '{}=={}'.format(package_name, expected_version) in versions, (
                'error: {} version should equal {}'.format(package_name, expected_version)
            )
    ''')
)


VERSION_REGEX = r'([\w-]+)==([^\s]+)'


def get_versions_from_constraint_file(constraint_file):
    constraint_file_text = constraint_file.read_text(encoding='utf8')

    versions = {}
    for package, version in re.findall(VERSION_REGEX, constraint_file_text):
        versions[package] = version

    return versions


@pytest.mark.parametrize('python_version', ['2.7', '3.5', '3.6', '3.8'])
def test_pinned_versions(tmp_path, python_version):
    if utils.platform == 'linux':
        pytest.skip('linux doesn\'t pin individual tool versions, it pins manylinux images instead')

    project_dir = tmp_path / 'project'
    project_with_expected_version_checks.generate(project_dir)

    build_environment = {}

    if python_version == '2.7':
        constraint_filename = 'constraints-python27.txt'
        build_pattern = '[cp]p27-*'
    elif python_version == '3.5':
        constraint_filename = 'constraints-python35.txt'
        build_pattern = '[cp]p35-*'
    elif python_version == '3.6':
        constraint_filename = 'constraints-python36.txt'
        build_pattern = '[cp]p36-*'
    elif python_version == '3.7':
        constraint_filename = 'constraints-python37.txt'
        build_pattern = '[cp]p37-*'
    else:
        constraint_filename = 'constraints.txt'
        build_pattern = '[cp]p38-*'

    constraint_file = cibuildwheel.util.resources_dir / constraint_filename
    constraint_versions = get_versions_from_constraint_file(constraint_file)

    for package in ['pip', 'setuptools', 'wheel', 'virtualenv']:
        env_name = f'EXPECTED_{package.upper()}_VERSION'
        build_environment[env_name] = constraint_versions[package]

    cibw_environment_option = ' '.join(
        [f'{k}={v}' for k, v in build_environment.items()]
    )

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': build_pattern,
        'CIBW_ENVIRONMENT': cibw_environment_option,
    })

    # also check that we got the right wheels
    if python_version == '2.7':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp27' in w or '-pp27' in w]
    elif python_version == '3.5':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp35' in w or '-pp35' in w]
    elif python_version == '3.6':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp36' in w or '-pp36' in w]
    elif python_version == '3.8':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp38' in w or '-pp38' in w]
    else:
        raise ValueError('unhandled python version')

    assert set(actual_wheels) == set(expected_wheels)


@pytest.mark.parametrize('python_version', ['2.7', '3.x'])
def test_dependency_constraints_file(tmp_path, python_version):
    if utils.platform == 'linux':
        pytest.skip('linux doesn\'t pin individual tool versions, it pins manylinux images instead')

    project_dir = tmp_path / 'project'
    project_with_expected_version_checks.generate(project_dir)

    tool_versions = {
        'pip': '20.0.2',
        'setuptools': '44.0.0' if python_version == '2.7' else '46.0.0',
        'wheel': '0.34.2',
        'virtualenv': '20.0.10',
    }

    constraints_file = tmp_path / 'constraints.txt'
    constraints_file.write_text(textwrap.dedent(
        '''
            pip=={pip}
            setuptools=={setuptools}
            wheel=={wheel}
            virtualenv=={virtualenv}
        '''.format(**tool_versions)
    ))

    build_environment = {}

    for package_name, version in tool_versions.items():
        env_name = f'EXPECTED_{package_name.upper()}_VERSION'
        build_environment[env_name] = version

    cibw_environment_option = ' '.join(
        [f'{k}={v}' for k, v in build_environment.items()]
    )

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': '[cp]p27-*' if python_version == '2.7' else '[cp]p3?-*',
        'CIBW_ENVIRONMENT': cibw_environment_option,
        'CIBW_DEPENDENCY_VERSIONS': str(constraints_file),
    })

    # also check that we got the right wheels
    if python_version == '2.7':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp27' in w or '-pp27' in w]
    else:
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if '-cp27' not in w and '-pp27' not in w]

    assert set(actual_wheels) == set(expected_wheels)
