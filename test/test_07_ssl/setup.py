import ssl
import sys
from setuptools import setup, Extension

if sys.version_info[0] == 2:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

if sys.version_info[0:2] == (3, 3):
    data = urlopen('https://www.nist.gov')
else:
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    data = urlopen('https://www.nist.gov', context=context)

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
