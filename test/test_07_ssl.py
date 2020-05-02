import os, textwrap
from . import utils
from .template_projects import CTemplateProject


project_with_ssl_tests = CTemplateProject(
    setup_py_add=textwrap.dedent(r'''
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

def test(tmpdir):
    # this test checks that SSL is working in the build environment using
    # some checks in setup.py.
    project_dir = str(tmpdir)
    project_with_ssl_tests.generate(project_dir)

    utils.cibuildwheel_run(project_dir)
