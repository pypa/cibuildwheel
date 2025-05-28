# Configuration methods

cibuildwheel can either be configured using environment variables, or from
config file such as `pyproject.toml`.

This page describes how to set options. For a full list of available options, see the [options reference](options.md).

## Environment variables {: #environment-variables}

Environment variables can be set in your CI config. For example, to configure
cibuildwheel to run tests, add the following YAML to your CI config file:

!!! tab "GitHub Actions"

    > .github/workflows/*.yml ([docs](https://help.github.com/en/actions/configuring-and-managing-workflows/using-environment-variables)) (can be global, in job, or in step)

    ```yaml
    env:
      CIBW_TEST_REQUIRES: pytest
      CIBW_TEST_COMMAND: "pytest {project}/tests"
    ```

!!! tab "Azure Pipelines"

    > azure-pipelines.yml ([docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/variables))

    ```yaml
    variables:
      CIBW_TEST_REQUIRES: pytest
      CIBW_TEST_COMMAND: "pytest {project}/tests"
    ```

!!! tab "Travis CI"

    > .travis.yml ([docs](https://docs.travis-ci.com/user/environment-variables/))

    ```yaml
    env:
      global:
        - CIBW_TEST_REQUIRES=pytest
        - CIBW_TEST_COMMAND="pytest {project}/tests"
    ```

!!! tab "CircleCI"

    > .circleci/config.yml ([docs](https://circleci.com/docs/2.0/configuration-reference/#environment))

    ```yaml
    jobs:
      job_name:
        environment:
          CIBW_TEST_REQUIRES: pytest
          CIBW_TEST_COMMAND: "pytest {project}/tests"
    ```

!!! tab "Gitlab CI"

    > .gitlab-ci.yml ([docs](https://docs.gitlab.com/ci/yaml/#variables))

    ```yaml
    linux:
      variables:
        CIBW_TEST_REQUIRES: pytest
        CIBW_TEST_COMMAND: "pytest {project}/tests"
    ```

!!! tab "Cirrus CI"

    > .cirrus.yml ([docs](https://cirrus-ci.org/guide/writing-tasks/#environment-variables))

    ```yaml
    env:
      CIBW_TEST_REQUIRES: pytest
      CIBW_TEST_COMMAND: "pytest {project}/tests"
    ```

## Configuration file {: #configuration-file}

You can configure cibuildwheel with a config file, such as `pyproject.toml`.
Options have the same names as the environment variable overrides, but are
placed in `[tool.cibuildwheel]` and are lower case, with dashes, following
common [TOML][https://toml.io] practice. Anything placed in subsections `linux`, `windows`,
`macos`, or `pyodide` will only affect those platforms. Lists can be used
instead of strings for items that are naturally a list. Multiline strings also
work just like in the environment variables. Environment variables will take
precedence if defined.

The example above using environment variables could have been written like this:

```toml
[tool.cibuildwheel]
test-requires = "pytest"
test-command = "pytest ./tests"
```

The complete set of defaults for the current version of cibuildwheel are shown below:

```toml
{% include "../cibuildwheel/resources/defaults.toml" %}
```


!!! tip
    Static configuration works across all CI systems, and can be used locally if
    you run `cibuildwheel --platform linux`. This is preferred, but environment
    variables are better if you need to change per-matrix element
    (`CIBW_BUILD` is often in this category, for example), or if you cannot or do
    not want to change a `pyproject.toml` file. You can specify a different file to
    use with `--config-file` on the command line, as well.

## Configuration overrides {: #overrides }

One feature specific to the configuration files is the ability to override
settings based on selectors. To use, add a ``tool.cibuildwheel.overrides``
array, and specify a ``select`` string. Then any options you set will only
apply to items that match that selector. These are applied in order, with later
matches overriding earlier ones if multiple selectors match. Environment
variables always override static configuration.

A few of the options below have special handling in overrides. A different
`before-all` will trigger a new container to launch on Linux, and cannot be
overridden on macOS or Windows.  Overriding the image on linux will also
trigger new containers, one per image. Some commands are not supported;
`output-dir`, build/skip/test_skip selectors, and architectures cannot be
overridden.

You can specify a table of overrides in `inherit={}`, any list or table in this
list will inherit from previous overrides or the main configuration. The valid
options are `"none"` (the default), `"append"`, and `"prepend"`.

#### Examples:

```toml
[tool.cibuildwheel.linux]
before-all = "yum install mylib"
test-command = "echo 'installed'"

[[tool.cibuildwheel.overrides]]
select = "*-musllinux*"
before-all = "apk add mylib"
```

This example will override the before-all command on musllinux only, but will
still run the test-command. Note the double brackets, this is an array in TOML,
which means it can be given multiple times.

```toml
[tool.cibuildwheel]
# Normal options, etc.
manylinux-x86_64-image = "manylinux_2_34"

[[tool.cibuildwheel.overrides]]
select = "cp38-*"
manylinux-x86_64-image = "manylinux2014"

[[tool.cibuildwheel.overrides]]
select = "cp3{9,10}-*"
manylinux-x86_64-image = "manylinux_2_28"
```

This example will build CPython 3.8 wheels on manylinux2014, CPython 3.9-3.10
wheels on manylinux_2_28, and manylinux_2_34 wheels for any newer Python
(like 3.10).

```toml
[tool.cibuildwheel]
environment = {FOO="BAR", "HAM"="EGGS"}
test-command = ["pyproject"]

[[tool.cibuildwheel.overrides]]
select = "cp311*"

inherit.test-command = "prepend"
test-command = ["pyproject-before"]

inherit.environment="append"
environment = {FOO="BAZ", "PYTHON"="MONTY"}

[[tool.cibuildwheel.overrides]]
select = "cp311*"
inherit.test-command = "append"
test-command = ["pyproject-after"]
```

This example will provide the command `"pyproject-before && pyproject && pyproject-after"`
on Python 3.11, and will have `environment = {FOO="BAZ", "PYTHON"="MONTY", "HAM"="EGGS"}`.


## Extending existing options {: #inherit }

In the TOML configuration, you can choose how tables and lists are inherited.
By default, all values are overridden completely (`"none"`) but sometimes you'd
rather `"append"` or `"prepend"` to an existing list or table. You can do this
with the `inherit` table in overrides.  For example, if you want to add an environment
variable for CPython 3.11, without `inherit` you'd have to repeat all the
original environment variables in the override. With `inherit`, it's just:

```toml
[[tool.cibuildwheel.overrides]]
select = "cp311*"
inherit.environment = "append"
environment.NEWVAR = "Added!"
```

For a table, `"append"` will replace a key if it exists, while `"prepend"` will
only add a new key, older keys take precedence.

Lists are also supported (and keep in mind that commands are lists). For
example, you can print a message before and after a wheel is repaired:

```toml
[[tool.cibuildwheel.overrides]]
select = "*"
inherit.repair-wheel-command = "prepend"
repair-wheel-command = "echo 'Before repair'"

[[tool.cibuildwheel.overrides]]
select = "*"
inherit.repair-wheel-command = "append"
repair-wheel-command = "echo 'After repair'"
```

As seen in this example, you can have multiple overrides match - they match top
to bottom, with the config being accumulated. If you need platform-specific
inheritance, you can use `select = "*-????linux_*"` for Linux, `select =
"*-win_*"` for Windows, and `select = "*-macosx_*"` for macOS. As always,
environment variables will completely override any TOML configuration.
