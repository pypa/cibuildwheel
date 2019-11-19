from setuptools import setup, Extension
import sys, os

# explode if environment isn't correct, as set in CIBW_ENVIRONMENT
CIBW_TEST_VAR = os.environ.get('CIBW_TEST_VAR')
CIBW_TEST_VAR_2 = os.environ.get('CIBW_TEST_VAR_2')
PATH = os.environ.get('PATH')

if CIBW_TEST_VAR != 'a b c':
    raise Exception('CIBW_TEST_VAR should equal "a b c". It was "%s"' % CIBW_TEST_VAR)
if CIBW_TEST_VAR_2 != '1':
    raise Exception('CIBW_TEST_VAR_2 should equal "1". It was "%s"' % CIBW_TEST_VAR_2)
if '/opt/cibw_test_path' not in PATH:
    raise Exception('PATH should contain "/opt/cibw_test_path". It was "%s"' % PATH)
if '$PATH' in PATH:
    raise Exception('$PATH should be expanded in PATH. It was "%s"' % PATH)


setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'])],
    version="0.1.0",
)
