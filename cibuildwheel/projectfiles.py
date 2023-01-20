from __future__ import annotations

import ast
import configparser
import contextlib
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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
        self.requires_python: str | None = None

    def visit(self, node: ast.AST) -> None:
        for inner_node in ast.walk(node):
            for child in ast.iter_child_nodes(inner_node):
                child.parent = inner_node  # type: ignore[attr-defined]
        super().visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        self.generic_visit(node)
        # Must not be nested in an if or other structure
        # This will be Module -> Expr -> Call -> keyword
        if (
            node.arg == "python_requires"
            and not hasattr(node.parent.parent.parent, "parent")  # type: ignore[attr-defined]
            and isinstance(node.value, Constant)
        ):
            self.requires_python = get_constant(node.value)


def setup_py_python_requires(content: str) -> str | None:
    try:
        tree = ast.parse(content)
        analyzer = Analyzer()
        analyzer.visit(tree)
        return analyzer.requires_python or None
    except Exception:  # pylint: disable=broad-except
        return None


def get_requires_python_str(package_dir: Path) -> str | None:
    """Return the python requires string from the most canonical source available, or None"""

    # Read in from pyproject.toml:project.requires-python
    with contextlib.suppress(FileNotFoundError):
        with (package_dir / "pyproject.toml").open("rb") as f1:
            info = tomllib.load(f1)
        with contextlib.suppress(KeyError, IndexError, TypeError):
            return str(info["project"]["requires-python"])

    # Read in from setup.cfg:options.python_requires
    config = configparser.ConfigParser()
    with contextlib.suppress(FileNotFoundError):
        config.read(package_dir / "setup.cfg")
        with contextlib.suppress(KeyError, IndexError, TypeError):
            return str(config["options"]["python_requires"])

    setup_py = package_dir / "setup.py"
    with contextlib.suppress(FileNotFoundError), setup_py.open(encoding="utf8") as f2:
        return setup_py_python_requires(f2.read())

    return None
