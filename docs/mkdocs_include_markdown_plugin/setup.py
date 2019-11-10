from setuptools import setup

setup(
    name='mkdocs_include_markdown_plugin',
    version='1.0',
    author='Joe Rickerby',
    license='Apache 2',
    packages=['mkdocs_include_markdown_plugin'],
    entry_points={
        'mkdocs.plugins': [
            'importmarkdown = mkdocs_include_markdown_plugin.plugin:ImportMarkdownPlugin',
        ]
    },
    zip_safe=False
)
