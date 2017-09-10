import subprocess, shlex, sys
from collections import namedtuple
import bashlex

NodeExecutionContext = namedtuple('NodeExecutionContext', ['environment', 'input'])

def evaluate(value, environment):
    if not value:
        # empty string evaluates to empty string
        # (but trips up bashlex)
        return ''

    command_node = bashlex.parsesingle(value)

    if len(command_node.parts) != 1:
        raise ValueError('"%s" has too many parts' % value)

    value_word_node = command_node.parts[0]
    
    return evaluate_node(
        value_word_node, 
        context=NodeExecutionContext(environment=environment, input=value)
    )


def evaluate_node(node, context):
    if node.kind == 'word':
        return evaluate_word_node(node, context=context)
    elif node.kind == 'commandsubstitution':
        return evaluate_command_node(node.command, context=context)
    elif node.kind == 'parameter':
        return evaluate_parameter_node(node, context=context)
    else:
        raise ValueError('Unsupported bash construct: "%s"' % node.word)


def evaluate_word_node(node, context):
    word_start = node.pos[0]
    word_end = node.pos[1]
    word_string = context.input[word_start:word_end]
    letters = list(word_string)

    for part in node.parts:
        part_start = part.pos[0] - word_start
        part_end = part.pos[1] - word_start

        # Set all the characters in the part to None
        for i in range(part_start, part_end):
            letters[i] = None

        letters[part_start] = evaluate_node(part, context=context)

    # remove the None letters and concat
    value = ''.join(l for l in letters if l is not None)

    # apply bash-like quotes/whitespace treatment
    return ' '.join(word.strip() for word in shlex.split(value))


def evaluate_command_node(node, context):
    words = [evaluate_node(part, context=context) for part in node.parts]
    command = ' '.join(words)
    output = subprocess.check_output(shlex.split(command), env=context.environment)

    if sys.version_info[0] >= 3:
        return output.decode('utf8', 'replace')
    else:
        return output

def evaluate_parameter_node(node, context):
    return context.environment.get(node.value, '')
