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
    "dev": [
        "click",
        "ghapi",
        "mypy>=0.800",
        "packaging>=20.8",
        "pip-tools",
        "pygithub",
        "pyyaml",
        "requests",
        "rich>=9.6",
        "typing-extensions",
    ],
}

extras["all"] = sum(extras.values(), [])
extras["dev"] += extras["test"]

setup(extras_require=extras)
