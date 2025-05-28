import dataclasses
import subprocess
from collections.abc import (
    Callable,
    Iterable,
    Mapping,
    Sequence,
)

import bashlex

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
