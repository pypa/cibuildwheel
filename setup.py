from setuptools import setup

extras = {
    "docs": [
        "mkdocs-include-markdown-plugin==2.8.0",
        "mkdocs==1.0.4",
        "pymdown-extensions",
    ],
    "test": [
        "jinja2",
        "pytest>=4",
        "pytest-timeout",
    ],
    "bin": [
        "click",
        "ghapi",
        "pip-tools",
        "pygithub",
        "pyyaml",
        "requests",
        "rich>=9.6",
        "packaging>=20.8",
    ],
}

extras["dev"] = [
    "mypy>=0.800",
    *extras["test"],
    *extras["bin"],
]

extras["all"] = sum(extras.values(), [])

setup(extras_require=extras)
