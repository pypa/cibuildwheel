from setuptools import setup

setup(
    name="mkdocs_execute_python_plugin",
    version="1.0",
    author="Joe Rickerby",
    license="Apache 2",
    packages=["mkdocs_execute_python_plugin"],
    entry_points={
        "mkdocs.plugins": [
            "execute-python = mkdocs_execute_python_plugin.plugin:ExecutePythonPlugin",
        ]
    },
    zip_safe=False,
)
