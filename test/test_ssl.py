import textwrap

import pytest

from . import test_projects, utils

project_with_ssl_tests = test_projects.new_c_project(
    setup_py_add=textwrap.dedent(
        r"""
            import ssl, time, urllib.request, urllib.error

            def check_https(context=None):
                # google hosts this endpoint that returns a 204 No Content, it's used for
                # connectivity checks in Android & Chrome
                url = "https://google.com/generate_204"

                for i in range(5):
                    try:
                        urllib.request.urlopen(url, context=context, timeout=5)
                        return
                    except (OSError, urllib.error.URLError) as e:
                        print(f"Attempt {i+1}: Could not connect to {url}: {e}")
                        time.sleep(2 ** i)  # Backoff: 1s, 2s, 4s, 8s...

                raise ConnectionError(f"Could not connect to {url} after retries.")

            check_https()
            check_https(context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
        """
    )
)


@pytest.mark.flaky(reruns=2)
def test(tmp_path):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.
    project_dir = tmp_path / "project"
    project_with_ssl_tests.generate(project_dir)

    actual_wheels = utils.cibuildwheel_run(project_dir)

    expected_wheels = utils.expected_wheels("spam", "0.1.0")
    assert set(actual_wheels) == set(expected_wheels)
