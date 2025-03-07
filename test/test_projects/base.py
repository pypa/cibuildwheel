from pathlib import Path
from typing import Any, Self

import jinja2

FilesDict = dict[str, str | jinja2.Template]
TemplateContext = dict[str, Any]


class TestProject:
    """
    An object that represents a project that can be built by cibuildwheel.
    Can be manipulated in tests by changing `files` and `template_context`.

    Write out to the filesystem using `generate`.
    """

    __test__ = False  # Have pytest ignore this class on `from .test_projects import TestProject`

    files: FilesDict
    template_context: TemplateContext

    def __init__(self) -> None:
        self.files = {}
        self.template_context = {}

    def generate(self, path: Path) -> None:
        for filename, content in self.files.items():
            file_path = path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with file_path.open("w", encoding="utf8") as f:
                if isinstance(content, jinja2.Template):
                    content = content.render(self.template_context)  # noqa: PLW2901

                f.write(content)

    def copy(self) -> Self:
        other = self.__class__()
        other.files = self.files.copy()
        other.template_context = self.template_context.copy()
        return other
