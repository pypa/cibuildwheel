import cgi
import re
from pathlib import Path

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

            file_path_abs = Path(page_src_path).parent / filename

            if not file_path_abs.exists():
                raise ValueError('file not found', filename)

            text_to_include = file_path_abs.read_text(encoding='utf8')

            # Allow good practice of having a final newline in the file
            if text_to_include.endswith('\n'):
                text_to_include = text_to_include[:-1]

            return text_to_include

        def found_includemarkdown_tag(match):
            filename = match.group('filename')
            start = match.group('start')
            end = match.group('end')

            file_path_abs = Path(page_src_path).parent / filename

            if not file_path_abs.exists():
                raise ValueError('file not found', filename)

            text_to_include = file_path_abs.read_text(encoding='utf8')

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
