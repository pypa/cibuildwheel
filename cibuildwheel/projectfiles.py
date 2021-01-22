import ast
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import toml

if sys.version_info < (3, 8):
    Constant = ast.Str

    def get_constant(x: ast.Str) -> str:
        return x.s
else:
    Constant = ast.Constant

    def get_constant(x: ast.Constant) -> Any:
        return x.value


class Analyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.requires_python: Optional[str] = None
        self.constants: Dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and isinstance(node.value, Constant)
                and isinstance(get_constant(node.value), str)
            ):
                self.constants[target.id] = get_constant(node.value)

    def visit_keyword(self, node: ast.keyword) -> None:
        self.generic_visit(node)
        if node.arg == "python_requires":
            if isinstance(node.value, Constant):
                self.requires_python = get_constant(node.value)
            elif isinstance(node.value, ast.Name):
                self.requires_python = self.constants.get(node.value.id)


def dig(d: Mapping[str, Any], *keys: str) -> Any:
    """
    Access a nested dictionary, returns None if any access is empty. Equivalent
    to #dig in Ruby.
    """

    try:
        for key in keys:
            d = d[key]
        return d
    except (KeyError, IndexError, TypeError):
        return None


class ProjectFiles:
    def __init__(self, package_dir: Path) -> None:
        self.package_dir = package_dir

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.package_dir!r})'

    @property
    def setup_py_path(self) -> Path:
        return self.package_dir / 'setup.py'

    @property
    def setup_cfg_path(self) -> Path:
        return self.package_dir / 'setup.cfg'

    @property
    def pyproject_toml_path(self) -> Path:
        return self.package_dir / 'pyproject.toml'

    # Can cache eventually if needed more than once
    # or just leave stateless.

    @property
    def pyproject_toml(self) -> Mapping[str, Any]:
        try:
            return toml.load(self.pyproject_toml_path)
        except FileNotFoundError:
            return {}

    @property
    def setup_cfg(self) -> Mapping[str, Any]:
        try:
            config = ConfigParser()
            config.read(self.setup_cfg_path)
            return config
        except FileNotFoundError:
            return {}

    def _setup_py_python_requires(self) -> Optional[str]:
        try:
            with open(self.setup_py_path) as f:
                tree = ast.parse(f.read())

            analyzer = Analyzer()
            analyzer.visit(tree)

            return analyzer.requires_python or None
        except Exception:
            return None

    def exists(self) -> bool:
        "Returns True if any project file exists"

        return self.pyproject_toml_path.exists() or self.setup_cfg_path.exists() or self.setup_py_path.exists()

    def get_requires_python_str(self) -> Optional[str]:
        "Return the python requires string from the most cannonical source available, or None"
        return (
            dig(self.pyproject_toml, 'project', 'requires-python')
            or dig(self.setup_cfg, 'options', 'python_requires')
            or self._setup_py_python_requires()
        )
