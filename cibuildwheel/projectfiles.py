import ast
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, Optional

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


def setup_py_python_requires(content: str) -> Optional[str]:
    try:
        tree = ast.parse(content)
        analyzer = Analyzer()
        analyzer.visit(tree)
        return analyzer.requires_python or None
    except Exception:
        return None


def get_requires_python_str(package_dir: Path) -> Optional[str]:
    "Return the python requires string from the most canonical source available, or None"

    setup_py = package_dir / 'setup.py'
    setup_cfg = package_dir / 'setup.cfg'
    pyproject_toml = package_dir / 'pyproject.toml'

    # Read in from pyproject.toml:project.requires-python
    try:
        info = toml.load(pyproject_toml)
        return str(info['project']['requires-python'])
    except (FileNotFoundError, KeyError, IndexError, TypeError):
        pass

    # Read in from setup.cfg:options.python_requires
    try:
        config = ConfigParser()
        config.read(setup_cfg)
        return str(config['options']['python_requires'])
    except (FileNotFoundError, KeyError, IndexError, TypeError):
        pass

    try:
        with open(setup_py) as f:
            return setup_py_python_requires(f.read())
    except FileNotFoundError:
        pass

    return None
