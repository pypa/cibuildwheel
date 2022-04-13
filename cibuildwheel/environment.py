import dataclasses
from typing import Any, Dict, List, Mapping, Optional, Sequence

import bashlex

from cibuildwheel.typing import Protocol

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


class EnvironmentAssignment(Protocol):
    name: str

    def evaluated_value(
        self,
        *,
        environment: Dict[str, str],
        executor: Optional[bashlex_eval.EnvironmentExecutor] = None,
    ) -> str:
        """Returns the value of this assignment, as evaluated in the environment"""


class EnvironmentAssignmentRaw:
    """
    An environment variable - a simple name/value pair
    """

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"{self.name}: {self.value}"

    def evaluated_value(self, **_: Any) -> str:
        return self.value


class EnvironmentAssignmentBash:
    """
    An environment variable, in bash syntax. The value can use bash constructs
    like "$OTHER_VAR" and "$(command arg1 arg2)".
    """

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
        return bashlex_eval.evaluate(self.value, environment=environment, executor=executor)

    def __repr__(self) -> str:
        return f"{self.name}={self.value}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EnvironmentAssignmentBash):
            return self.name == other.name and self.value == other.value
        return False


@dataclasses.dataclass
class ParsedEnvironment:
    assignments: List[EnvironmentAssignment]

    def __init__(self, assignments: Sequence[EnvironmentAssignment]) -> None:
        self.assignments = list(assignments)

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

    def add(self, name: str, value: str) -> None:
        self.assignments.append(EnvironmentAssignmentRaw(name=name, value=value))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({[repr(a) for a in self.assignments]!r})"


def parse_environment(env_string: str) -> ParsedEnvironment:
    env_items = split_env_items(env_string)
    assignments = [EnvironmentAssignmentBash(item) for item in env_items]
    return ParsedEnvironment(assignments=assignments)
