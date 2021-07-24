import os

from cibuildwheel.environment import parse_environment


def test_basic_parsing():
    environment_recipe = parse_environment("VAR=1 VBR=2")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {"VAR": "1", "VBR": "2"}
    assert environment_cmds == ["export VAR=1", "export VBR=2"]


def test_quotes():
    environment_recipe = parse_environment("A=1 VAR=\"1 NOT_A_VAR=2\" VBR='vbr'")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {"A": "1", "VAR": "1 NOT_A_VAR=2", "VBR": "vbr"}
    assert environment_cmds == ["export A=1", 'export VAR="1 NOT_A_VAR=2"', "export VBR='vbr'"]


def test_inheritance():
    environment_recipe = parse_environment("PATH=$PATH:/usr/local/bin")

    environment_dict = environment_recipe.as_dictionary(prev_environment={"PATH": "/usr/bin"})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {"PATH": "/usr/bin:/usr/local/bin"}
    assert environment_cmds == ["export PATH=$PATH:/usr/local/bin"]


def test_shell_eval():
    environment_recipe = parse_environment('VAR="$(echo "a   test" string)"')

    env_copy = os.environ.copy()
    env_copy.pop("VAR", None)

    environment_dict = environment_recipe.as_dictionary(prev_environment=env_copy)
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict["VAR"] == "a   test string"
    assert environment_cmds == ['export VAR="$(echo "a   test" string)"']


def test_shell_eval_and_env():
    environment_recipe = parse_environment('VAR="$(echo "$PREV_VAR" string)"')

    environment_dict = environment_recipe.as_dictionary(prev_environment={"PREV_VAR": "1 2 3"})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {"PREV_VAR": "1 2 3", "VAR": "1 2 3 string"}
    assert environment_cmds == ['export VAR="$(echo "$PREV_VAR" string)"']


def test_empty_var():
    environment_recipe = parse_environment("CFLAGS=")

    environment_dict = environment_recipe.as_dictionary(prev_environment={"CFLAGS": "-Wall"})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {"CFLAGS": ""}
    assert environment_cmds == ["export CFLAGS="]


def test_no_vars():
    environment_recipe = parse_environment("")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})
    environment_cmds = environment_recipe.as_shell_commands()

    assert environment_dict == {}
    assert environment_cmds == []


def test_no_vars_pass_through():
    environment_recipe = parse_environment("")

    environment_dict = environment_recipe.as_dictionary(
        prev_environment={"CIBUILDWHEEL": "awesome"}
    )

    assert environment_dict == {"CIBUILDWHEEL": "awesome"}


def test_operators_inside_eval():
    environment_recipe = parse_environment('SOMETHING="$(echo a; echo b; echo c)"')

    # pass the existing process env so PATH is available
    environment_dict = environment_recipe.as_dictionary(os.environ.copy())

    assert environment_dict.get("SOMETHING") == "a\nb\nc"


def test_substitution_with_backslash():
    environment_recipe = parse_environment('PATH2="somewhere_else;$PATH1"')

    # pass the existing process env so PATH is available
    environment_dict = environment_recipe.as_dictionary(prev_environment={"PATH1": "c:\\folder\\"})

    assert environment_dict.get("PATH2") == "somewhere_else;c:\\folder\\"


def test_awkwardly_quoted_variable():
    environment_recipe = parse_environment(
        'VAR2=something"like this""$VAR1"$VAR1$(echo "there is more")"$(echo "and more!")"'
    )

    # pass the existing process env so PATH is available
    environment_dict = environment_recipe.as_dictionary({"VAR1": "but wait"})

    assert (
        environment_dict.get("VAR2") == "somethinglike thisbut waitbut waitthere is moreand more!"
    )
