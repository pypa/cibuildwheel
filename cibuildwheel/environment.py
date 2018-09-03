import bashlex
from . import bashlex_eval


class EnvironmentParseError(Exception):
    pass


def parse_environment(env_string):
    env_items = split_env_items(env_string)
    assignments = [EnvironmentAssignment(item) for item in env_items]
    return ParsedEnvironment(assignments=assignments)


def split_env_items(env_string):
    '''Splits space-separated variable assignments into a list of individual assignments.

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
    '''
    if not env_string:
        return []

    command_node = bashlex.parsesingle(env_string)
    result = []

    for word_node in command_node.parts:
        part_string = env_string[word_node.pos[0]:word_node.pos[1]]
        result.append(part_string)

    return result


class EnvironmentAssignment(object):
    def __init__(self, assignment):
        name, equals, value = assignment.partition('=')
        if not equals:
            raise EnvironmentParseError(assignment)
        self.name = name
        self.value = value

    def evaluated_value(self, environment):
        '''Returns the value of this assignment, as evaluated in the environment'''
        return bashlex_eval.evaluate(self.value, environment=environment)

    def as_shell_assignment(self):
        return 'export %s=%s' % (self.name, self.value)

    def __repr__(self):
        return '%s=%s' % (self.name, self.value)


class ParsedEnvironment(object):
    def __init__(self, assignments):
        self.assignments = assignments

    def as_dictionary(self, prev_environment):
        environment = prev_environment.copy()

        for assignment in self.assignments:
            value = assignment.evaluated_value(environment=environment)
            environment[assignment.name] = value

        return environment

    def as_shell_commands(self):
        return [a.as_shell_assignment() for a in self.assignments]

    def __repr__(self):
        return 'ParsedEnvironment(%r)' % [repr(a) for a in self.assignments]
