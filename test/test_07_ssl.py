import os, textwrap
from . import utils


def test(tmpdir):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.

    project_dir = str(tmpdir)

    utils.generate_project(
        path=project_dir,
        setup_py_add=textwrap.dedent('''
            import ssl
            import sys

            if sys.version_info[0] == 2:
                from urllib2 import urlopen
            else:
                from urllib.request import urlopen

            if sys.version_info[0:2] == (3, 3):
                data = urlopen("https://www.nist.gov")
            else:
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                data = urlopen("https://www.nist.gov", context=context)
        ''')
    )

    utils.cibuildwheel_run(project_dir)
