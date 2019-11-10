import mkdocs, re, os, io, cgi

TAG_REGEX_PATTERN = re.compile(
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

        def found_import_markdown_tag(match):
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
                '<!-- BEGIN INCLUDE %s %s %s -->' % (
                    filename, cgi.escape(start), cgi.escape(end)
                )
                + text_to_include
                + '<!-- END INCLUDE -->'
            )

        markdown = re.sub(TAG_REGEX_PATTERN, found_import_markdown_tag, markdown)
        return markdown
    