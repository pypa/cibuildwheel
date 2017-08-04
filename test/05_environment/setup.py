from setuptools import setup, Extension
import os

setup(
    name="spam",
    ext_modules=[Extension('spam', sources=['spam.c'], define_macros=[tuple(define.split(':')) for define in os.environ.get('SPAM_DEFINES', '').split(';')])],
    version=os.environ.get('SPAM_VERSION', ''),
)
