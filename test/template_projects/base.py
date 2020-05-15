import os
import jinja2
from typing import Union, Dict, Any


FilesDict = Dict[str, Union[str, jinja2.Template]]
TemplateContext = Dict[str, Any]


class TemplateProject:
    files: FilesDict
    template_context: TemplateContext

    def __init__(self):
        self.files = {}
        self.template_context = {}

    def generate(self, path: str):
        for filename, content in self.files.items():
            file_path = os.path.join(path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf8') as f:
                if isinstance(content, jinja2.Template):
                    content = content.render(self.template_context)

                f.write(content)

    def copy(self):
        other = TemplateProject()
        other.files = self.files.copy()
        other.template_context = self.template_context.copy()
        return other
