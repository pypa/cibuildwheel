from __future__ import annotations

import textwrap

from . import test_projects, utils

project_with_ssl_tests = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
        import ssl

        from urllib.request import urlopen, Request

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        data = urlopen("https://www.nist.gov", context=context)
        data = urlopen("https://raw.githubusercontent.com/pypa/cibuildwheel/main/CI.md", context=context)
        data = urlopen("https://raw.githubusercontent.com/pypa/cibuildwheel/main/CI.md")
        # try a cloudflare-hosted site
        data = urlopen(
            Request(
                "https://anaconda.org/multibuild-wheels-staging/openblas-libs/files",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 ; (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3"
                }
            )
        )
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
