import ast
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional

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

    def visit(self, content: ast.AST) -> None:
        for node in ast.walk(content):
            for child in ast.iter_child_nodes(node):
                child.parent = node  # type: ignore
        super().visit(content)

    def visit_keyword(self, node: ast.keyword) -> None:
        self.generic_visit(node)
        if node.arg == "python_requires":
            # Must not be nested in an if or other structure
            # This will be Module -> Expr -> Call -> keyword
            if not hasattr(node.parent.parent.parent, "parent") and isinstance(  # type: ignore
                node.value, Constant
            ):
                self.requires_python = get_constant(node.value)


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

    # Read in from pyproject.toml:project.requires-python
    try:
        info = toml.load(package_dir / "pyproject.toml")
        return str(info["project"]["requires-python"])
    except (FileNotFoundError, KeyError, IndexError, TypeError):
        pass

    # Read in from setup.cfg:options.python_requires
    try:
        config = ConfigParser()
        config.read(package_dir / "setup.cfg")
        return str(config["options"]["python_requires"])
    except (FileNotFoundError, KeyError, IndexError, TypeError):
        pass

    try:
        with open(package_dir / "setup.py") as f:
            return setup_py_python_requires(f.read())
    except FileNotFoundError:
        pass

    return None
