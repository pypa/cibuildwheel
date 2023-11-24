from __future__ import annotations

from setuptools import setup

extras = {
    "docs": [
        "mkdocs-include-markdown-plugin==2.8.0",
        "mkdocs==1.3.1",
        "jinja2>=3.1.2",
        "pymdown-extensions",
        "mkdocs-macros-plugin",
    ],
    "test": [
        "jinja2",
        "pytest>=6",
        "pytest-timeout",
        "pytest-xdist",
        "build",
        "tomli_w",
        "validate-pyproject",
    ],
    "bin": [
        "click",
        "pip-tools",
        "pygithub",
        "pyyaml",
        "requests",
        "rich>=9.6",
        "packaging>=21.0",
    ],
}

extras["dev"] = [
    *extras["test"],
    *extras["bin"],
]

setup(extras_require=extras)
