import os, inspect, textwrap
from . import utils
from .template_projects import CTemplateProject


project_with_environment_asserts = CTemplateProject(
    setup_py_add=textwrap.dedent(r'''
        import os

        # explode if environment isn't correct, as set in CIBW_ENVIRONMENT
        CIBW_TEST_VAR = os.environ.get("CIBW_TEST_VAR")
        CIBW_TEST_VAR_2 = os.environ.get("CIBW_TEST_VAR_2")
        PATH = os.environ.get("PATH")

        if CIBW_TEST_VAR != "a b c":
            raise Exception('CIBW_TEST_VAR should equal "a b c". It was "%s"' % CIBW_TEST_VAR)
        if CIBW_TEST_VAR_2 != "1":
            raise Exception('CIBW_TEST_VAR_2 should equal "1". It was "%s"' % CIBW_TEST_VAR_2)
        if "/opt/cibw_test_path" not in PATH:
            raise Exception('PATH should contain "/opt/cibw_test_path". It was "%s"' % PATH)
        if "$PATH" in PATH:
            raise Exception('$PATH should be expanded in PATH. It was "%s"' % PATH)
    ''')
)


def test(tmpdir):
    project_dir = str(tmpdir)
    project_with_environment_asserts.generate(project_dir)

    # write some information into the CIBW_ENVIRONMENT, for expansion and
    # insertion into the environment by cibuildwheel. This is checked
    # in setup_py_add
    actual_wheels = utils.cibuildwheel_run(
        project_dir,
        add_env={
            "CIBW_ENVIRONMENT": """CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH=$PATH:/opt/cibw_test_path""",
            "CIBW_ENVIRONMENT_WINDOWS": '''CIBW_TEST_VAR="a b c" CIBW_TEST_VAR_2=1 CIBW_TEST_VAR_3="$(echo 'test string 3')" PATH="$PATH;/opt/cibw_test_path"''',
        },
    )

    # also check that we got the right wheels built
    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
