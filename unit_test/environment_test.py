import os
import sys

from cibuildwheel.environment import parse_environment

# this command is equivalent to Unix 'echo', but works on Windows too
PYTHON_ECHO = f"'{sys.executable}' -c \"import sys; print(*sys.argv[1:])\""


def test_basic_parsing():
    environment_recipe = parse_environment("VAR=1 VBR=2")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})

    assert environment_dict == {"VAR": "1", "VBR": "2"}


def test_quotes():
    environment_recipe = parse_environment("A=1 VAR=\"1 NOT_A_VAR=2\" VBR='vbr'")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})

    assert environment_dict == {"A": "1", "VAR": "1 NOT_A_VAR=2", "VBR": "vbr"}


def test_inheritance():
    environment_recipe = parse_environment("PATH=$PATH:/usr/local/bin")

    environment_dict = environment_recipe.as_dictionary(prev_environment={"PATH": "/usr/bin"})

    assert environment_dict == {"PATH": "/usr/bin:/usr/local/bin"}


def test_shell_eval():
    environment_recipe = parse_environment(f'VAR="$({PYTHON_ECHO} "a   test" string)"')

    env_copy = os.environ.copy()
    env_copy.pop("VAR", None)

    environment_dict = environment_recipe.as_dictionary(prev_environment=env_copy)

    assert environment_dict["VAR"] == "a   test string"


def test_shell_eval_and_env():
    environment_recipe = parse_environment(f'VAR="$({PYTHON_ECHO} "$PREV_VAR" string)"')

    prev_environment = {**os.environ, "PREV_VAR": "1 2 3"}
    environment_dict = environment_recipe.as_dictionary(prev_environment=prev_environment)

    assert environment_dict == {**prev_environment, "VAR": "1 2 3 string"}


def test_empty_var():
    environment_recipe = parse_environment("CFLAGS=")

    environment_dict = environment_recipe.as_dictionary(prev_environment={"CFLAGS": "-Wall"})

    assert environment_dict == {"CFLAGS": ""}


def test_no_vars():
    environment_recipe = parse_environment("")

    environment_dict = environment_recipe.as_dictionary(prev_environment={})

    assert environment_dict == {}


def test_no_vars_pass_through():
    environment_recipe = parse_environment("")

    environment_dict = environment_recipe.as_dictionary(
        prev_environment={"CIBUILDWHEEL": "awesome"}
    )

    assert environment_dict == {"CIBUILDWHEEL": "awesome"}


def test_operators_inside_eval():
    environment_recipe = parse_environment(
        f'SOMETHING="$({PYTHON_ECHO} a; {PYTHON_ECHO} b; {PYTHON_ECHO} c)"'
    )

    # pass the existing process env so subcommands can be run in the evaluation
    environment_dict = environment_recipe.as_dictionary(prev_environment=os.environ.copy())

    assert environment_dict.get("SOMETHING") == "a\nb\nc"


def test_substitution_with_backslash():
    environment_recipe = parse_environment('PATH2="somewhere_else;$PATH1"')

    environment_dict = environment_recipe.as_dictionary(prev_environment={"PATH1": "c:\\folder\\"})

    assert environment_dict.get("PATH2") == "somewhere_else;c:\\folder\\"


def test_awkwardly_quoted_variable():
    environment_recipe = parse_environment(
        f'VAR2=something"like this""$VAR1"$VAR1$({PYTHON_ECHO} "there is more")"$({PYTHON_ECHO} "and more!")"'
    )

    prev_environment = {**os.environ, "VAR1": "but wait"}
    environment_dict = environment_recipe.as_dictionary(prev_environment=prev_environment)

    assert (
        environment_dict.get("VAR2") == "somethinglike thisbut waitbut waitthere is moreand more!"
    )
