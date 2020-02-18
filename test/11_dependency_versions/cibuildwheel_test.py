import os
import re
import pytest
import textwrap
import cibuildwheel.util

import utils


def get_version_from_constraint_file(package_name, constraint_file):
    version_pattern = package_name + r'==([^\s]+)'

    with open(constraint_file, encoding='utf8') as f:
        constraint_file_text = f.read()

    match = re.search(version_pattern, constraint_file_text)

    if not match:
        raise Exception("couldn't find version spec matching " + version_pattern)

    return match.group(1)


@pytest.mark.parametrize('python_version', ['2.7', '3.x'])
def test_pinned_versions(python_version):
    if utils.platform == 'linux':
        pytest.skip('linux doesn\'t pin individual tool versions, it pins manylinux images instead')

    project_dir = os.path.dirname(__file__)

    build_environment = {}

    if python_version == '2.7':
        constraint_filename = 'constraints-python27.txt'
    else:
        constraint_filename = 'constraints.txt'

    constraint_file = os.path.join(cibuildwheel.util.resources_dir, constraint_filename)

    for package in ['pip', 'setuptools', 'wheel', 'virtualenv']:
        env_name = 'EXPECTED_{}_VERSION'.format(package.upper())
        build_environment[env_name] = get_version_from_constraint_file(package, constraint_file)

    cibw_environment_option = ' '.join(['{}={}'.format(k, v) for k, v in build_environment.items()])
    cibw_build_option = 'cp27-*' if python_version == '2.7' else 'cp3*'

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_BUILD': cibw_build_option,
        'CIBW_ENVIRONMENT': cibw_environment_option,
    })

    # also check that we got the right wheels
    if python_version == '2.7':
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if w.startswith('cp27')]
    else:
        expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')
                           if w.startswith('cp3')]

    assert set(actual_wheels) == set(expected_wheels)


def test_dependency_constraints_file(tmp_path):
    if utils.platform == 'linux':
        pytest.skip('linux doesn\'t pin individual tool versions, it pins manylinux images instead')

    project_dir = os.path.dirname(__file__)

    tool_versions = {
        'pip': '19.2.3',
        'setuptools': '43.0.0',
        'wheel': '0.33.6',
        'virtualenv': '16.7.8',
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
        env_name = 'EXPECTED_{}_VERSION'.format(package_name.upper())
        build_environment[env_name] = version

    cibw_environment_option = ' '.join(
        ['{}={}'.format(k, v) for k, v in build_environment.items()]
    )

    # build and test the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        'CIBW_ENVIRONMENT': cibw_environment_option,
        'CIBW_DEPENDENCY_VERSIONS': str(constraints_file),
    })

    # also check that we got the right wheels
    expected_wheels = [w for w in utils.expected_wheels('spam', '0.1.0')]
    assert set(actual_wheels) == set(expected_wheels)
