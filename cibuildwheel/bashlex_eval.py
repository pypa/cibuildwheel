from __future__ import annotations

__lazy_modules__ = {"bashlex", "subprocess"}

import dataclasses
import subprocess

import bashlex

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        Iterable,
        Mapping,
        Sequence,
    )

    # a function that takes a command and the environment, and returns the result
    EnvironmentExecutor = Callable[[list[str], dict[str, str]], str]


def local_environment_executor(command: Sequence[str], env: Mapping[str, str]) -> str:
    return subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, check=True).stdout


@dataclasses.dataclass(frozen=True, kw_only=True)
class NodeExecutionContext:
    environment: dict[str, str]
    input: str
    executor: EnvironmentExecutor


def evaluate(
    value: str, environment: Mapping[str, str], executor: EnvironmentExecutor | None = None
) -> str:
    if not value:
        # empty string evaluates to empty string
        # (but trips up bashlex)
        return ""

    command_node = bashlex.parsesingle(value)

    if len(command_node.parts) != 1:
        msg = f"{value!r} has too many parts"
        raise ValueError(msg)

    value_word_node = command_node.parts[0]

    return evaluate_node(
        value_word_node,
        context=NodeExecutionContext(
            environment=dict(environment),
            input=value,
            executor=executor or local_environment_executor,
        ),
    )


def evaluate_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    if node.kind == "word":
        return evaluate_word_node(node, context=context)
    elif node.kind == "commandsubstitution":
        node_result = evaluate_command_node(node.command, context=context)
        # bash removes training newlines in command substitution
        return node_result.rstrip()
    elif node.kind == "parameter":
        return evaluate_parameter_node(node, context=context)
    else:
        msg = f"Unsupported bash construct: {node.kind!r}"
        raise ValueError(msg)


def evaluate_word_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    # Part positions index the raw source; node.word is quote-removed. A
    # leftmost text replace expands a literal "\$X" that precedes a real "$X".
    offsets = _expansion_offsets(node, context.input)
    if offsets is None:
        return _substitute_parts_leftmost(node, context)

    # Evaluate left to right like bash, then splice from the end so earlier
    # offsets stay valid.
    part_values = [evaluate_node(part, context=context) for part in node.parts]
    value: str = node.word
    for (start, end), part_value in reversed(list(zip(offsets, part_values, strict=True))):
        value = value[:start] + part_value + value[end:]
    return value


def _expansion_offsets(node: bashlex.ast.node, source: str) -> list[tuple[int, int]] | None:
    """Spans of each expansion in the quote-removed word, or None if unaligned."""
    if not node.parts:
        return []
    start, end = node.pos
    if start < 0 or end > len(source) or end < start:
        return None
    raw = source[start:end]
    # bashlex keeps a single quote only when the whole token starts with `"`.
    double_quoted = raw.startswith('"')
    parts = {p.pos[0] - start: (n, p.pos[1] - start) for n, p in enumerate(node.parts)}
    if len(parts) != len(node.parts):
        return None
    found: dict[int, tuple[int, int]] = {}
    out: list[str] = []
    w = i = 0
    while i < len(raw):
        if i in parts:
            n, j = parts.pop(i)
            if j <= i:
                return None
            chunk = raw[i:j]
            found[n] = (w, w + len(chunk))
            out.append(chunk)
            w, i = w + len(chunk), j
            continue
        char = raw[i]
        i += 1
        if char == "\\" and i < len(raw):
            out.append(raw[i])
            w += 1
            i += 1
        elif (char == "'" and double_quoted) or char not in "\\\"'":
            out.append(char)
            w += 1
    if parts or "".join(out) != node.word:
        return None
    return [found[n] for n in range(len(node.parts))]


def _substitute_parts_leftmost(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    value: str = node.word

    for part in node.parts:
        part_string = context.input[part.pos[0] : part.pos[1]]
        part_value = evaluate_node(part, context=context)

        if part_string not in value:
            msg = f"bash parse failed. part {part_string!r} not found in {value!r}. Word was {node.word!r}. Full input was {context.input!r}"
            raise RuntimeError(msg)

        value = value.replace(part_string, part_value, 1)

    return value


def evaluate_command_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    if any(n.kind == "operator" for n in node.parts):
        return evaluate_nodes_as_compound_command(node.parts, context=context)
    else:
        return evaluate_nodes_as_simple_command(node.parts, context=context)


def evaluate_nodes_as_compound_command(
    nodes: Sequence[bashlex.ast.node], context: NodeExecutionContext
) -> str:
    # bashlex doesn't support any operators besides ';' inside command
    # substitutions, so we only need to handle that case. We do so assuming
    # that `set -o errexit` is on, because it's easier to code!

    result = ""
    for node in nodes:
        if node.kind == "command":
            result += evaluate_command_node(node, context=context)
        elif node.kind == "operator":
            if node.op != ";":
                msg = f"Unsupported bash operator: {node.op!r}"
                raise ValueError(msg)
        else:
            msg = f"Unsupported bash node in compound command: {node.kind!r}"
            raise ValueError(msg)

    return result


def evaluate_nodes_as_simple_command(
    nodes: Iterable[bashlex.ast.node], context: NodeExecutionContext
) -> str:
    command = [evaluate_node(part, context=context) for part in nodes]
    return context.executor(command, context.environment)


def evaluate_parameter_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    return context.environment.get(node.value, "")
