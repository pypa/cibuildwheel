import cgi
import io
import os
import re

import mkdocs

INCLUDE_TAG_REGEX = re.compile(
    r'''
        {% # opening tag
        \s*
        include # directive name
        \s+
        "(?P<filename>[^"]+)" # "filename"
        \s*
        %} # closing tag
    ''',
    flags=re.VERBOSE,
)

INCLUDEMARKDOWN_TAG_REGEX = re.compile(
    r'''
        {% # opening tag
        \s*
        includemarkdown # directive name
        \s+
        "(?P<filename>[^"]+)" # "filename"
        (?:\s+start="(?P<start>[^"]+)")? # optional start expression
        (?:\s+end="(?P<end>[^"]+)")? # optional end expression
        \s*
        %} # closing tag
    ''',
    flags=re.VERBOSE,
)


class ImportMarkdownPlugin(mkdocs.plugins.BasePlugin):
    def on_page_markdown(self, markdown, page, **kwargs):
        page_src_path = page.file.abs_src_path

        def found_include_tag(match):
            filename = match.group('filename')

            file_path_abs = os.path.join(os.path.dirname(page_src_path), filename)

            if not os.path.exists(file_path_abs):
                raise ValueError('file not found', filename)

            with io.open(file_path_abs, encoding='utf8') as f:
                text_to_include = f.read()

            # Allow good practice of having a final newline in the file
            if text_to_include.endswith('\n'):
                text_to_include = text_to_include[:-1]

            return text_to_include

        def found_includemarkdown_tag(match):
            filename = match.group('filename')
            start = match.group('start')
            end = match.group('end')

            file_path_abs = os.path.join(os.path.dirname(page_src_path), filename)

            if not os.path.exists(file_path_abs):
                raise ValueError('file not found', filename)

            with io.open(file_path_abs, encoding='utf8') as f:
                text_to_include = f.read()

            if start:
                _, _, text_to_include = text_to_include.partition(start)

            if end:
                text_to_include, _, _ = text_to_include.partition(end)

            return (
                '<!-- BEGIN INCLUDE %s %s %s -->\n' % (
                    filename, cgi.escape(start or ''), cgi.escape(end or '')
                )
                + text_to_include
                + '\n<!-- END INCLUDE -->'
            )

        markdown = re.sub(INCLUDE_TAG_REGEX, found_include_tag, markdown)
        markdown = re.sub(INCLUDEMARKDOWN_TAG_REGEX, found_includemarkdown_tag, markdown)
        return markdown
