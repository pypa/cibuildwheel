import textwrap

from . import utils
from . import test_projects

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(r'''
        import sys, os

        # assert that the Python version as written to pythonversion.txt in the CIBW_BEFORE_BUILD step
        # is the same one as is currently running.
        version_file = 'c:\\pythonversion.txt' if sys.platform == 'win32' else '/tmp/pythonversion.txt'
        with open(version_file) as f:
            stored_version = f.read()
        print('stored_version', stored_version)
        print('sys.version', sys.version)
        assert stored_version == sys.version

        # check that the executable also was written
        executable_file = 'c:\\pythonexecutable.txt' if sys.platform == 'win32' else '/tmp/pythonexecutable.txt'
        with open(executable_file) as f:
            stored_executable = f.read()
        print('stored_executable', stored_executable)
        print('sys.executable', sys.executable)
        # windows/mac are case insensitive
        assert os.path.realpath(stored_executable).lower() == os.path.realpath(sys.executable).lower()

        if sys.platform == 'linux':
            cwd_file = '/tmp/cwd.txt'
            with open(cwd_file) as f:
                stored_cwd = f.read()
            assert stored_cwd == '/project'
    ''')
)


def test(tmp_path):
    project_dir = tmp_path / 'project'
    project_with_before_build_asserts.generate(project_dir)

    before_build = textwrap.dedent('''
        python -c "import sys; open('{output_dir}pythonversion.txt', 'w').write(sys.version)" &&
        python -c "import sys; open('{output_dir}pythonexecutable.txt', 'w').write(sys.executable)" &&
        python -c "import os; open('{output_dir}cwd.txt', 'w').write(os.getcwd())"
    ''')

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        # write python version information to a temporary file, this is
        # checked in setup.py
        'CIBW_BEFORE_BUILD': before_build.format(output_dir="/tmp/"),
        'CIBW_BEFORE_BUILD_WINDOWS': before_build.format(output_dir="c:\\"),
    })

    # also check that we got the right wheels
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
