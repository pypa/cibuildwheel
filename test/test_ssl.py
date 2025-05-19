import textwrap

from . import test_projects, utils

project_with_ssl_tests = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import ssl

        from urllib.request import urlopen

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        # badssl.com is a HTTPS test server that can be used to test SSL connections
        data = urlopen("https://tls-v1-2.badssl.com", context=context)
        data = urlopen("https://tls-v1-2.badssl.com")
        """
    )
)


def test(tmp_path):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.
    project_dir = tmp_path / "project"
    project_with_ssl_tests.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir)

    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
