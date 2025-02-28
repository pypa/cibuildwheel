import ast
import configparser
import contextlib
from pathlib import Path
from typing import Any

import dependency_groups


def get_parent(node: ast.AST | None, depth: int = 1) -> ast.AST | None:
    for _ in range(depth):
        node = getattr(node, "parent", None)
    return node


def is_main(parent: ast.AST | None) -> bool:
    if parent is None:
        return False

    # This would be much nicer with 3.10's pattern matching!
    if not isinstance(parent, ast.If):
        return False
    if not isinstance(parent.test, ast.Compare):
        return False

    try:
        (op,) = parent.test.ops
        (comp,) = parent.test.comparators
    except ValueError:
        return False

    if not isinstance(op, ast.Eq):
        return False

    values = {comp, parent.test.left}

    mains = {x for x in values if isinstance(x, ast.Constant) and x.value == "__main__"}
    if len(mains) != 1:
        return False
    consts = {x for x in values if isinstance(x, ast.Name) and x.id == "__name__"}

    return len(consts) == 1


class Analyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.requires_python: str | None = None

    def visit(self, node: ast.AST) -> None:
        for inner_node in ast.walk(node):
            for child in ast.iter_child_nodes(inner_node):
                child.parent = inner_node  # type: ignore[attr-defined]
        super().visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        # Must not be nested except for if __name__ == "__main__"

        self.generic_visit(node)
        # This will be Module -> Expr -> Call -> keyword
        parent = get_parent(node, 4)
        unnested = parent is None

        # This will be Module -> If -> Expr -> Call -> keyword
        name_main_unnested = (
            parent is not None and get_parent(parent) is None and is_main(get_parent(node, 3))
        )

        if (
            node.arg == "python_requires"
            and isinstance(node.value, ast.Constant)
            and (unnested or name_main_unnested)
        ):
            self.requires_python = node.value.value


def setup_py_python_requires(content: str) -> str | None:
    try:
        tree = ast.parse(content)
        analyzer = Analyzer()
        analyzer.visit(tree)
        return analyzer.requires_python or None
    except Exception:  # pylint: disable=broad-except
        return None


def get_requires_python_str(package_dir: Path, pyproject_toml: dict[str, Any] | None) -> str | None:
    """Return the python requires string from the most canonical source available, or None"""

    # Read in from pyproject.toml:project.requires-python
    with contextlib.suppress(KeyError, IndexError, TypeError):
        return str((pyproject_toml or {})["project"]["requires-python"])

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


def resolve_dependency_groups(
    pyproject_toml: dict[str, Any] | None, *groups: str
) -> tuple[str, ...]:
    """
    Get the packages in dependency-groups for a package.
    """

    if not groups:
        return ()

    if pyproject_toml is None:
        msg = f"Didn't find a pyproject.toml, so can't read [dependency-groups] {groups!r} from it!"
        raise FileNotFoundError(msg)

    try:
        dependency_groups_toml = pyproject_toml["dependency-groups"]
    except KeyError:
        msg = f"Didn't find [dependency-groups] in pyproject.toml, which is needed to resolve {groups!r}."
        raise KeyError(msg) from None

    return dependency_groups.resolve(dependency_groups_toml, *groups)
