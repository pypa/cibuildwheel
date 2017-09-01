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
    '''
    return list(bashlex.split(env_string))


class EnvironmentAssignment(object):
    def __init__(self, assignment):
        name, equals, value = assignment.partition('=')
        if not equals:
            raise EnvironmentParseError(assignment)
        self.name = name
        self.value = value

        if value:
            command_node = bashlex.parsesingle(value)

            if len(command_node.parts) != 1:
                raise ValueError('"%s" has too many parts' % value)

            self.value_word_node = command_node.parts[0]
        else:
            self.value_word_node = None

    def evaluated_value(self, environment):
        '''Returns the value of this assignment, as evaluated in the environment'''
        if self.value_word_node:
            return bashlex_eval.evaluate_node(self.value_word_node, environment=environment)
        else:
            return ''

    def as_shell_assignment(self):
        return 'export %s=%s' % (self.name, self.value)


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
