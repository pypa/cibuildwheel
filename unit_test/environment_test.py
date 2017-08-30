from cibuildwheel.environment import parse_environment


def test_basic_parsing():
    environment_recipe = parse_environment('VAR=1 VBR=2')

    environment_dict = environment_recipe.as_dictionary(
        prev_environment={},
        shell=lambda cmd: '')
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {'VAR': '1', 'VBR': '2'}
    assert environment_cmds == ['export VAR=1', 'export VBR=2']

def test_quotes():
    environment_recipe = parse_environment('A=1 VAR="1 NOT_A_VAR=2" VBR=\'vbr\'')

    environment_dict = environment_recipe.as_dictionary(
        prev_environment={},
        shell=lambda cmd: '')
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {'A': '1', 'VAR': '1 NOT_A_VAR=2', 'VBR': 'vbr'}
    assert environment_cmds == ['export A=1', 'export VAR="1 NOT_A_VAR=2"', 'export ABR=vbr']

def test_inheritance():
    environment_recipe = parse_environment('PATH=$PATH:/usr/local/bin')

    environment_dict = environment_recipe.as_dictionary(
        prev_environment={'PATH': '/usr/bin'},
        shell=lambda cmd: '')
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {'PATH': '/usr/bin:/usr/local/bin'}
    assert environment_cmds == ['export PATH=$PATH:/usr/local/bin']
