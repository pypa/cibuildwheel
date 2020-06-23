import shlex
import subprocess

from typing import Dict, NamedTuple, Callable, Optional

import bashlex  # type: ignore


# a function that takes a shell command and the environment, and returns the result
EnvironmentExecutor = Callable[[str, Dict[str, str]], str]


def local_environment_executor(command: str, env: Dict[str, str]) -> str:
    return subprocess.check_output(shlex.split(command), env=env, universal_newlines=True)


class NodeExecutionContext(NamedTuple):
    environment: Dict[str, str]
    input: str
    executor: EnvironmentExecutor


def evaluate(value: str, environment: Dict[str, str], executor: Optional[EnvironmentExecutor] = None) -> str:
    if not value:
        # empty string evaluates to empty string
        # (but trips up bashlex)
        return ''

    command_node = bashlex.parsesingle(value)

    if len(command_node.parts) != 1:
        raise ValueError(f'"{value}" has too many parts')

    value_word_node = command_node.parts[0]

    return evaluate_node(
        value_word_node,
        context=NodeExecutionContext(environment=environment, input=value, executor=executor or local_environment_executor)
    )


def evaluate_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    if node.kind == 'word':
        return evaluate_word_node(node, context=context)
    elif node.kind == 'commandsubstitution':
        return evaluate_command_node(node.command, context=context)
    elif node.kind == 'parameter':
        return evaluate_parameter_node(node, context=context)
    else:
        raise ValueError(f'Unsupported bash construct: "{node.word}"')


def evaluate_word_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    word_start = node.pos[0]
    word_end = node.pos[1]
    word_string = context.input[word_start:word_end]
    letters = list(word_string)

    for part in node.parts:
        part_start = part.pos[0] - word_start
        part_end = part.pos[1] - word_start

        # Set all the characters in the part to None
        for i in range(part_start, part_end):
            letters[i] = ''

        letters[part_start] = evaluate_node(part, context=context)

    # remove the None letters and concat
    value = ''.join(letters)

    # apply bash-like quotes/whitespace treatment
    return ' '.join(word.strip() for word in shlex.split(value))


def evaluate_command_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    words = [evaluate_node(part, context=context) for part in node.parts]
    command = ' '.join(words)
    return context.executor(command, context.environment)


def evaluate_parameter_node(node: bashlex.ast.node, context: NodeExecutionContext) -> str:
    return context.environment.get(node.value, '')
