from setuptools import setup

extras = {
    "docs": [
        "mkdocs-include-markdown-plugin==2.8.0",
        "mkdocs==1.0.4",  # Doesn't support Python 3.10+
        "jinja2==3.0.3",
        "pymdown-extensions",
        "mkdocs-macros-plugin",
        "markdown<3.4",  # Breaks mkdocs 1.0.4
    ],
    "test": [
        "jinja2",
        "pytest>=6",
        "pytest-timeout",
        "pytest-xdist",
        "build",
        "tomli_w",
    ],
    "bin": [
        "click",
        "ghapi",
        "pip-tools",
        "pygithub",
        "pyyaml",
        "requests",
        "rich>=9.6",
        "packaging>=21.0",
    ],
    "mypy": [
        "mypy>=0.901",
        "types-jinja2",
        "types-certifi",
        "types-toml",
        "types-jinja2",
        "types-pyyaml",
        "types-click",
        "types-requests",
    ],
}

extras["dev"] = [
    *extras["mypy"],
    *extras["test"],
    *extras["bin"],
]

extras["all"] = sum(extras.values(), [])

setup(extras_require=extras)
