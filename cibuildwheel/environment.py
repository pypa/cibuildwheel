from typing import Dict, List, Mapping, Optional

import bashlex

from . import bashlex_eval


class EnvironmentParseError(Exception):
    pass


def split_env_items(env_string: str) -> List[str]:
    """Splits space-separated variable assignments into a list of individual assignments.

    >>> split_env_items('VAR=abc')
    ['VAR=abc']
    >>> split_env_items('VAR="a string" THING=3')
    ['VAR="a string"', 'THING=3']
    >>> split_env_items('VAR="a string" THING=\\'single "quotes"\\'')
    ['VAR="a string"', 'THING=\\'single "quotes"\\'']
    >>> split_env_items('VAR="dont \\\\"forget\\\\" about backslashes"')
    ['VAR="dont \\\\"forget\\\\" about backslashes"']
    >>> split_env_items('PATH="$PATH;/opt/cibw_test_path"')
    ['PATH="$PATH;/opt/cibw_test_path"']
    >>> split_env_items('PATH2="something with spaces"')
    ['PATH2="something with spaces"']
    """
    if not env_string:
        return []

    command_node = bashlex.parsesingle(env_string)
    result = []

    for word_node in command_node.parts:
        part_string = env_string[word_node.pos[0] : word_node.pos[1]]
        result.append(part_string)

    return result


class EnvironmentAssignment:
    def __init__(self, assignment: str):
        name, equals, value = assignment.partition("=")
        if not equals:
            raise EnvironmentParseError(assignment)
        self.name = name
        self.value = value

    def evaluated_value(
        self,
        environment: Dict[str, str],
        executor: Optional[bashlex_eval.EnvironmentExecutor] = None,
    ) -> str:
        """Returns the value of this assignment, as evaluated in the environment"""
        return bashlex_eval.evaluate(self.value, environment=environment, executor=executor)

    def as_shell_assignment(self) -> str:
        return f"export {self.name}={self.value}"

    def __repr__(self) -> str:
        return f"{self.name}={self.value}"


class ParsedEnvironment:
    def __init__(self, assignments: List[EnvironmentAssignment]):
        self.assignments = assignments

    def as_dictionary(
        self,
        prev_environment: Mapping[str, str],
        executor: Optional[bashlex_eval.EnvironmentExecutor] = None,
    ) -> Dict[str, str]:
        environment = dict(**prev_environment)

        for assignment in self.assignments:
            value = assignment.evaluated_value(environment=environment, executor=executor)
            environment[assignment.name] = value

        return environment

    def as_shell_commands(self) -> List[str]:
        return [a.as_shell_assignment() for a in self.assignments]

    def __repr__(self) -> str:
        return f"ParsedEnvironment({[repr(a) for a in self.assignments]!r})"


def parse_environment(env_string: str) -> ParsedEnvironment:
    env_items = split_env_items(env_string)
    assignments = [EnvironmentAssignment(item) for item in env_items]
    return ParsedEnvironment(assignments=assignments)
