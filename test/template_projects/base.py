import os
import io
import jinja2
from typing import Union, Dict, Any


FilesDict = Dict[str, Union[str, jinja2.Template]]


class TemplateProject:
    default_files: FilesDict = {}
    files: FilesDict
    context: Dict[str, Any]

    def __init__(self, *, extra_files: FilesDict):
        self.files = self.default_files.copy()
        self.files.update(extra_files)
        self.context = {}

    def generate(self, path):
        for filename, content in self.files.items():
            file_path = os.path.join(path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with io.open(file_path, 'w', encoding='utf8') as f:
                if isinstance(content, jinja2.Template):
                    content = content.render(self.context)

                f.write(content)
