import os
import textwrap

from . import utils
from . import test_projects

project_with_before_build_asserts = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(r'''
        # assert that the Python version as written to text_info.txt in the CIBW_BEFORE_ALL step
        # is the same one as is currently running.
        with open("text_info.txt") as f:
            stored_text = f.read()

        print("## stored text: " + stored_text)
        assert stored_text == "sample text 123"
    ''')
)


def test(tmp_path):
    project_dir = tmp_path / 'project'
    project_with_before_build_asserts.generate(project_dir)

    with open(os.path.join(project_dir, "text_info.txt"), mode='w') as ff:
        print("dummy text", file=ff)

    # build the wheels
    actual_wheels = utils.cibuildwheel_run(project_dir, add_env={
        # write python version information to a temporary file, this is
        # checked in setup.py
        'CIBW_BEFORE_ALL': '''python -c "import os;open('{project}/text_info.txt', 'w').write('sample text '+os.environ.get('TEST_VAL', ''))"''',
        'CIBW_ENVIRONMENT': "TEST_VAL='123'"
    })

    # also check that we got the right wheels
    os.remove(os.path.join(project_dir, "text_info.txt"))
    expected_wheels = utils.expected_wheels('spam', '0.1.0')
    assert set(actual_wheels) == set(expected_wheels)
