#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='cibuildwheel',
    version='0.9.4',
    install_requires=['bashlex'],
    description="Build Python wheels on CI with minimal configuration.",
    long_description='For readme please see http://github.com/joerick/cibuildwheel',
    author="Joe Rickerby",
    author_email='joerick@mac.com',
    url='https://github.com/joerick/cibuildwheel',
    packages=['cibuildwheel',],
    license="BSD",
    zip_safe=False,
    keywords='ci wheel packaging pypi travis appveyor macos linux windows',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Build Tools',
    ],
    entry_points={
        'console_scripts': [
            'cibuildwheel = cibuildwheel.__main__:main',
        ],
    },
)
