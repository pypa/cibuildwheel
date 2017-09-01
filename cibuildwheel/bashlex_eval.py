import subprocess, shlex


def evaluate_node(node, environment):
    if node.kind == 'word':
        return evaluate_word_node(node, environment=environment)
    elif node.kind == 'commandsubstitution':
        return evaluate_command_node(node.command, environment=environment)
    elif node.kind == 'parameter':
        return evaluate_parameter_node(node, environment=environment)
    else:
        raise ValueError('Unsupported bash construct: "%s"' % node.word)


def evaluate_word_node(node, environment):
    letters = list(node.word)

    for part in node.parts:
        part_start = part.pos[0]
        part_end = part.pos[1]

        # Set all the characters in the part to None
        for i in range(part_start, part_end):
            letters[i] = None

        letters[part_start] = evaluate_node(part, environment=environment)

    # remove the None letters and concat
    return ''.join(l for l in letters if l is not None)


def evaluate_command_node(node, environment):
    words = [evaluate_node(part, environment=environment) for part in node.parts]
    command = ' '.join(words)
    return subprocess.check_output(shlex.split(command), env=environment)


def evaluate_parameter_node(node, environment):
    return environment.get(node.value, '')
