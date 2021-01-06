from pathlib import Path
from typing import Any, Dict, Union

import jinja2

FilesDict = Dict[str, Union[str, jinja2.Template]]
TemplateContext = Dict[str, Any]


class TestProject:
    '''
    An object that represents a project that can be built by cibuildwheel.
    Can be manipulated in tests by changing `files` and `template_context`.

    Write out to the filesystem using `generate`.
    '''
    __test__ = False  # Have pytest ignore this class on `from .test_projects import TestProject`

    files: FilesDict
    template_context: TemplateContext

    def __init__(self):
        self.files = {}
        self.template_context = {}

    def generate(self, path: Path):
        for filename, content in self.files.items():
            file_path = path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with file_path.open('w', encoding='utf8') as f:
                if isinstance(content, jinja2.Template):
                    content = content.render(self.template_context)

                f.write(content)

    def copy(self):
        other = TestProject()
        other.files = self.files.copy()
        other.template_context = self.template_context.copy()
        return other
