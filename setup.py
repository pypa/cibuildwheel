# -*- coding: utf-8 -*-
from pathlib import Path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

this_directory = Path(__file__).parent
long_description = (this_directory / 'README.md').read_text(encoding='utf-8')

setup(
    name='cibuildwheel',
    version='1.7.3',
    install_requires=['bashlex!=0.13', 'toml', 'certifi'],
    description="Build Python wheels on CI with minimal configuration.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Joe Rickerby",
    author_email='joerick@mac.com',
    url='https://github.com/joerick/cibuildwheel',
    project_urls={
        'Changelog': 'https://github.com/joerick/cibuildwheel#changelog',
        'Documentation': 'https://cibuildwheel.readthedocs.io/',
    },
    packages=['cibuildwheel', ],
    license="BSD",
    zip_safe=False,
    package_data={
        'cibuildwheel': ['resources/*'],
    },
    # Supported python versions
    python_requires='>=3.6',
    keywords='ci wheel packaging pypi travis appveyor macos linux windows',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
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
