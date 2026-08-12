---
title: Configuration
ref: configuration
---

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

## Configuration file {: #configuration-file}

You can configure cibuildwheel with a config file, such as `pyproject.toml`.
Options have the same names as the environment variable overrides, but are
placed in `[tool.cibuildwheel]` and are lower case, with dashes, following
common [TOML](https://toml.io) practice. Anything placed in subsections
named after a platform will only affect those platforms. Platform-specific
values replace the corresponding global value for that platform; table options
are not merged key by key unless you configure [inheritance](#inherit). Lists can
be used instead of strings for items that are naturally a list. Multiline strings
also work just like in the environment variables. Environment variable overrides,
such as `CIBW_TEST_COMMAND` and `CIBW_TEST_COMMAND_LINUX`, take precedence if
defined.

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
array, and specify a ``select`` string, referencing the [build identifier](options.md#build-skip) (not wheel name!).
Then any options you set will only
apply to items that match that selector. These are applied in order, with later
matches overriding earlier ones if multiple selectors match. Environment
variables always override static configuration.

A few of the options below have special handling in overrides. A different
`before-all` will trigger a new container to launch on Linux, and cannot be
overridden on macOS or Windows.  Overriding the image on linux will also
trigger new containers, one per image.

!!! note "Some commands are not supported"

    The ``output-dir``, ``build``, ``skip``, ``test_skip`` selectors, and architectures cannot be overridden.

By default, values in an override replace values from the main configuration or
earlier overrides. You can instead [extend a list or table option](#inherit) by
setting an `inherit` rule for it.

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
select = "cp39-*"
manylinux-x86_64-image = "manylinux2014"

[[tool.cibuildwheel.overrides]]
select = "cp3{10,11}-*"
manylinux-x86_64-image = "manylinux_2_28"
```

This example will build CPython 3.9 wheels on manylinux2014, CPython 3.10-3.11
wheels on manylinux_2_28, and manylinux_2_34 wheels for any newer Python
(like 3.14).

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


## Option inheritance {: #inherit }

As cibuildwheel reads its configuration, each layer normally replaces the value
from the previous layer. The layers, from lowest to highest precedence, are:

1. cibuildwheel's defaults
2. `[tool.cibuildwheel]`
3. `[tool.cibuildwheel.<platform>]`
4. matching `[[tool.cibuildwheel.overrides]]` entries, in order
5. `CIBW_<OPTION>`
6. `CIBW_<OPTION>_<PLATFORM>`

For list and table options, you can use an `inherit` rule to merge a value with
the value accumulated from the preceding layers instead. The available rules
are `"none"` (replace the previous value, the default), `"append"`, and
`"prepend"`.

In `pyproject.toml`, set the rule in the same table as the value it applies to.
For example, this adds Twine checks to the default audit configuration:

```toml
[tool.cibuildwheel]
inherit.audit-requires = "append"
inherit.audit-command = "append"
audit-requires = ["twine"]
audit-command = "twine check {wheel}"
```

Inheritance can also combine global and platform-specific configuration. This
example runs a Linux-specific setup command before the global command:

```toml
[tool.cibuildwheel]
before-all = "make -C third_party_lib"

[tool.cibuildwheel.linux]
inherit.before-all = "prepend"
before-all = "yum install -y libffi-devel"
```

The same mechanism remains available in overrides. For example, if you want to
add an environment variable for CPython 3.11, without `inherit` you'd have to
repeat all the original environment variables in the override. With `inherit`,
it's just:

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
to bottom, with the config being accumulated.

For environment variables, specify the rules in `CIBW_INHERIT`. Rules are
separated by semicolons and use lowercase option names. A rule without an
explicit value defaults to `append`:

```yaml
CIBW_AUDIT_REQUIRES: twine
CIBW_AUDIT_COMMAND: "twine check {wheel}"
CIBW_INHERIT: "audit-requires; audit-command"
```

Rules in `CIBW_INHERIT` apply to both the plain `CIBW_<OPTION>` variable and
the platform-specific `CIBW_<OPTION>_<PLATFORM>` variable. To set rules that
apply only to the platform-specific variables, use `CIBW_INHERIT_<PLATFORM>`;
those rules take precedence over `CIBW_INHERIT` for the platform-specific
variables. For example, this prepends `CIBW_BEFORE_ALL_LINUX` to the value
accumulated from the lower-precedence layers:

```yaml
CIBW_BEFORE_ALL_LINUX: yum install -y libffi-devel
CIBW_INHERIT_LINUX: "before-all: prepend"
```
