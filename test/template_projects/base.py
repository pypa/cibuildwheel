import os
import io
from typing import List, Tuple


class TemplateProject:
    files: List[Tuple[str, str]]

    def __init__(self, files):
        self.files = files

    def generate(self, path):
        for filename, content in self.files:
            file_path = os.path.join(path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with io.open(file_path, 'w', encoding='utf8') as f:
                f.write(content)
