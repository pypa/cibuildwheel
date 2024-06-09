# Options

## Setting options

cibuildwheel can either be configured using environment variables, or from
config file such as `pyproject.toml`.

### Environment variables {: #environment-variables}

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

!!! tab "AppVeyor"

    > appveyor.yml ([docs](https://www.appveyor.com/docs/build-configuration/#environment-variables))

    ```yaml
    environment:
      global:
        CIBW_TEST_REQUIRES: pytest
        CIBW_TEST_COMMAND: "pytest {project}\\tests"
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

    > .gitlab-ci.yml ([docs](https://docs.gitlab.com/ee/ci/variables/README.html#create-a-custom-variable-in-gitlab-ciyml))

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

### Configuration file {: #configuration-file}

You can configure cibuildwheel with a config file, such as `pyproject.toml`.
Options have the same names as the environment variable overrides, but are
placed in `[tool.cibuildwheel]` and are lower case, with dashes, following
common [TOML][] practice. Anything placed in subsections `linux`, `windows`,
`macos`, or `pyodide` will only affect those platforms. Lists can be used
instead of strings for items that are naturally a list. Multiline strings also
work just like in the environment variables. Environment variables will take
precedence if defined.

The example above using environment variables could have been written like this:

```toml
[tool.cibuildwheel]
test-requires = "pytest"
test-command = "pytest {project}/tests"
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

### Configuration overrides {: #overrides }

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

##### Examples:

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
manylinux-x86_64-image = "manylinux2014"

[[tool.cibuildwheel.overrides]]
select = "cp36-*"
manylinux-x86_64-image = "manylinux1"

[[tool.cibuildwheel.overrides]]
select = "cp3{7,8,9}-*"
manylinux-x86_64-image = "manylinux2010"
```

This example will build CPython 3.6 wheels on manylinux1, CPython 3.7-3.9
wheels on manylinux2010, and manylinux2014 wheels for any newer Python
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


### Extending existing options {: #inherit }

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

## Options summary

<div class="options-toc"></div>

## Build selection

### `CIBW_PLATFORM` {: #platform}

> Override the auto-detected target platform

Options: `auto` `linux` `macos` `windows` `pyodide`

Default: `auto`

`auto` will build wheels for the current platform.

- For `linux`, you need [Docker or Podman](#container-engine) running, on Linux, macOS, or Windows.
- For `macos` and `windows`, you need to be running on the respective system, with a working compiler toolchain installed - Xcode Command Line tools for macOS, and MSVC for Windows.
- For `pyodide` you need to be on an x86-64 linux runner and `python3.12` must be available in `PATH`.

This option can also be set using the [command-line option](#command-line) `--platform`. This option is not available in the `pyproject.toml` config.

!!! tip
    You can use this option to locally debug your cibuildwheel config on Linux, instead of pushing to CI to test every change. For example:

    ```bash
    export CIBW_BUILD='cp37-*'
    export CIBW_TEST_COMMAND='pytest {package}/tests'
    cibuildwheel --platform linux .
    ```

    Linux builds are the easiest to test locally, because all the build tools are supplied in the container, and they run exactly the same locally as in CI.

    This is even more convenient if you store your cibuildwheel config in [`pyproject.toml`](#configuration-file).

    You can also run a single identifier with `--only <identifier>`. This will
    not require `--platform` or `--arch`, and will override any build/skip
    configuration.

### `CIBW_BUILD`, `CIBW_SKIP` {: #build-skip}

> Choose the Python versions to build

List of builds to build and skip. Each build has an identifier like `cp38-manylinux_x86_64` or `cp37-macosx_x86_64` - you can list specific ones to build and cibuildwheel will only build those, and/or list ones to skip and cibuildwheel won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `CIBW_BUILD` and does not match `CIBW_SKIP` will be built.

When setting the options, you can use shell-style globbing syntax, as per [fnmatch](https://docs.python.org/3/library/fnmatch.html) with the addition of curly bracket syntax `{option1,option2}`, provided by [bracex](https://pypi.org/project/bracex/). All the build identifiers supported by cibuildwheel are shown below:

<div class="build-id-table-marker"></div>

|               | macOS                                                                  | Windows                                             | Linux Intel                                                                                         | Linux Other                                                                                                                                                     |
|---------------|------------------------------------------------------------------------|-----------------------------------------------------|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Python 3.6    | cp36-macosx_x86_64                                                     | cp36-win_amd64<br/>cp36-win32                       | cp36-manylinux_x86_64<br/>cp36-manylinux_i686<br/>cp36-musllinux_x86_64<br/>cp36-musllinux_i686     | cp36-manylinux_aarch64<br/>cp36-manylinux_ppc64le<br/>cp36-manylinux_s390x<br/>cp36-musllinux_aarch64<br/>cp36-musllinux_ppc64le<br/>cp36-musllinux_s390x       |
| Python 3.7    | cp37-macosx_x86_64                                                     | cp37-win_amd64<br/>cp37-win32                       | cp37-manylinux_x86_64<br/>cp37-manylinux_i686<br/>cp37-musllinux_x86_64<br/>cp37-musllinux_i686     | cp37-manylinux_aarch64<br/>cp37-manylinux_ppc64le<br/>cp37-manylinux_s390x<br/>cp37-musllinux_aarch64<br/>cp37-musllinux_ppc64le<br/>cp37-musllinux_s390x       |
| Python 3.8    | cp38-macosx_x86_64<br/>cp38-macosx_universal2<br/>cp38-macosx_arm64    | cp38-win_amd64<br/>cp38-win32                       | cp38-manylinux_x86_64<br/>cp38-manylinux_i686<br/>cp38-musllinux_x86_64<br/>cp38-musllinux_i686     | cp38-manylinux_aarch64<br/>cp38-manylinux_ppc64le<br/>cp38-manylinux_s390x<br/>cp38-musllinux_aarch64<br/>cp38-musllinux_ppc64le<br/>cp38-musllinux_s390x       |
| Python 3.9    | cp39-macosx_x86_64<br/>cp39-macosx_universal2<br/>cp39-macosx_arm64    | cp39-win_amd64<br/>cp39-win32<br/>cp39-win_arm64    | cp39-manylinux_x86_64<br/>cp39-manylinux_i686<br/>cp39-musllinux_x86_64<br/>cp39-musllinux_i686     | cp39-manylinux_aarch64<br/>cp39-manylinux_ppc64le<br/>cp39-manylinux_s390x<br/>cp39-musllinux_aarch64<br/>cp39-musllinux_ppc64le<br/>cp39-musllinux_s390x       |
| Python 3.10   | cp310-macosx_x86_64<br/>cp310-macosx_universal2<br/>cp310-macosx_arm64 | cp310-win_amd64<br/>cp310-win32<br/>cp310-win_arm64 | cp310-manylinux_x86_64<br/>cp310-manylinux_i686<br/>cp310-musllinux_x86_64<br/>cp310-musllinux_i686 | cp310-manylinux_aarch64<br/>cp310-manylinux_ppc64le<br/>cp310-manylinux_s390x<br/>cp310-musllinux_aarch64<br/>cp310-musllinux_ppc64le<br/>cp310-musllinux_s390x |
| Python 3.11   | cp311-macosx_x86_64<br/>cp311-macosx_universal2<br/>cp311-macosx_arm64 | cp311-win_amd64<br/>cp311-win32<br/>cp311-win_arm64 | cp311-manylinux_x86_64<br/>cp311-manylinux_i686<br/>cp311-musllinux_x86_64<br/>cp311-musllinux_i686 | cp311-manylinux_aarch64<br/>cp311-manylinux_ppc64le<br/>cp311-manylinux_s390x<br/>cp311-musllinux_aarch64<br/>cp311-musllinux_ppc64le<br/>cp311-musllinux_s390x |
| Python 3.12   | cp312-macosx_x86_64<br/>cp312-macosx_universal2<br/>cp312-macosx_arm64 | cp312-win_amd64<br/>cp312-win32<br/>cp312-win_arm64 | cp312-manylinux_x86_64<br/>cp312-manylinux_i686<br/>cp312-musllinux_x86_64<br/>cp312-musllinux_i686 | cp312-manylinux_aarch64<br/>cp312-manylinux_ppc64le<br/>cp312-manylinux_s390x<br/>cp312-musllinux_aarch64<br/>cp312-musllinux_ppc64le<br/>cp312-musllinux_s390x |
| Python 3.13   | cp313-macosx_x86_64<br/>cp313-macosx_universal2<br/>cp313-macosx_arm64 | cp313-win_amd64<br/>cp313-win32<br/>cp313-win_arm64 | cp313-manylinux_x86_64<br/>cp313-manylinux_i686<br/>cp313-musllinux_x86_64<br/>cp313-musllinux_i686 | cp313-manylinux_aarch64<br/>cp313-manylinux_ppc64le<br/>cp313-manylinux_s390x<br/>cp313-musllinux_aarch64<br/>cp313-musllinux_ppc64le<br/>cp313-musllinux_s390x |
| PyPy3.7 v7.3  | pp37-macosx_x86_64                                                     | pp37-win_amd64                                      | pp37-manylinux_x86_64<br/>pp37-manylinux_i686                                                       | pp37-manylinux_aarch64                                                                                                                                          |
| PyPy3.8 v7.3  | pp38-macosx_x86_64<br/>pp38-macosx_arm64                               | pp38-win_amd64                                      | pp38-manylinux_x86_64<br/>pp38-manylinux_i686                                                       | pp38-manylinux_aarch64                                                                                                                                          |
| PyPy3.9 v7.3  | pp39-macosx_x86_64<br/>pp39-macosx_arm64                               | pp39-win_amd64                                      | pp39-manylinux_x86_64<br/>pp39-manylinux_i686                                                       | pp39-manylinux_aarch64                                                                                                                                          |
| PyPy3.10 v7.3 | pp310-macosx_x86_64<br/>pp310-macosx_arm64                             | pp310-win_amd64                                     | pp310-manylinux_x86_64<br/>pp310-manylinux_i686                                                     | pp310-manylinux_aarch64                                                                                                                                         |

The list of supported and currently selected build identifiers can also be retrieved by passing the `--print-build-identifiers` flag to cibuildwheel.
The format is `python_tag-platform_tag`, with tags similar to those in [PEP 425](https://www.python.org/dev/peps/pep-0425/#details).

For CPython, the minimally supported macOS version is 10.9; for PyPy 3.7, macOS 10.13 or higher is required.

Windows arm64 platform support is experimental.

For an experimental WebAssembly build with `--platform pyodide`,
`cp312-pyodide_wasm32` is the only platform identifier.

See the [cibuildwheel 1 documentation](https://cibuildwheel.pypa.io/en/1.x/) for past end-of-life versions of Python, and PyPy2.7.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Only build on CPython 3.6
    CIBW_BUILD: cp36-*

    # Skip building on CPython 3.6 on the Mac
    CIBW_SKIP: cp36-macosx_x86_64

    # Skip building on CPython 3.8 on the Mac
    CIBW_SKIP: cp38-macosx_x86_64

    # Skip building on CPython 3.6 on all platforms
    CIBW_SKIP: cp36-*

    # Skip CPython 3.6 on Windows
    CIBW_SKIP: cp36-win*

    # Skip CPython 3.6 on 32-bit Windows
    CIBW_SKIP: cp36-win32

    # Skip CPython 3.6 and CPython 3.7
    CIBW_SKIP: cp36-* cp37-*

    # Skip Python 3.6 on Linux
    CIBW_SKIP: cp36-manylinux*

    # Skip 32-bit builds
    CIBW_SKIP: "*-win32 *-manylinux_i686"

    # Disable building PyPy wheels on all platforms
    CIBW_SKIP: pp*
    ```

    Separate multiple selectors with a space.

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Only build on CPython 3.6
    build = "cp36-*"

    # Skip building on CPython 3.6 on the Mac
    skip = "cp36-macosx_x86_64"

    # Skip building on CPython 3.8 on the Mac
    skip = "cp38-macosx_x86_64"

    # Skip building on CPython 3.6 on all platforms
    skip = "cp36-*"

    # Skip CPython 3.6 on Windows
    skip = "cp36-win*"

    # Skip CPython 3.6 on 32-bit Windows
    skip = "cp36-win32"

    # Skip CPython 3.6 and CPython 3.7
    skip = ["cp36-*", "cp37-*"]

    # Skip Python 3.6 on Linux
    skip = "cp36-manylinux*"

    # Skip 32-bit builds
    skip = ["*-win32", "*-manylinux_i686"]

    # Disable building PyPy wheels on all platforms
    skip = "pp*"
    ```

    It is generally recommended to set `CIBW_BUILD` as an environment variable, though `skip`
    tends to be useful in a config file; you can statically declare that you don't
    support PyPy, for example.

<style>
  .build-id-table-marker + table {
    font-size: 90%;
    white-space: nowrap;
  }
  .rst-content .build-id-table-marker + table td,
  .rst-content .build-id-table-marker + table th {
    padding: 4px 4px;
  }
  .build-id-table-marker + table td:not(:first-child) {
    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
    font-size: 85%;
  }
  dt code {
    font-size: 100%;
    background-color: rgba(41, 128, 185, 0.1);
    padding: 0;
  }
</style>

### `CIBW_FREE_THREADED_SUPPORT` {: #free-threaded-support}

> Choose whether free-threaded variants should be built

[PEP 703](https://www.python.org/dev/peps/pep-0703) introduced variants of CPython that can be built without the Global Interpreter Lock (GIL).
Those variants are also known as free-threaded / no-gil.

Building for free-threaded variants is disabled by default.

Building can be enabled by setting this option to `true`. The free-threaded compatible wheels will be built in addition to the standard wheels.

This option doesn't support overrides.
If you need to enable/disable it per platform or python version, set this option to `true` and use [`CIBW_BUILD`](#build-skip)/[`CIBW_SKIP`](#build-skip) options to filter the builds.

The build identifiers for those variants have a `t` suffix in their `python_tag` (e.g. `cp313t-manylinux_x86_64`)

!!! note
    This feature is experimental: [What’s New In Python 3.13](https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython)

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Enable free-threaded support
    CIBW_FREE_THREADED_SUPPORT: 1

    # Skip building free-threaded compatible wheels on Windows
    CIBW_FREE_THREADED_SUPPORT: 1
    CIBW_SKIP: *t-win*
    ```

    It is generally recommended to use `free-threaded-support` in a config file as you can statically declare that you
    support free-threaded builds.

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Enable free-threaded support
    free-threaded-support = true

    # Skip building free-threaded compatible wheels on Windows
    free-threaded-support = true
    skip = "*t-win*"
    ```

### `CIBW_ARCHS` {: #archs}
> Change the architectures built on your machine by default.

A list of architectures to build.

On macOS, this option can be used to [cross-compile](faq.md#cross-compiling)
between `x86_64`, `universal2` and `arm64`.

On Linux, this option can be used to build non-native architectures under
emulation. See [this guide](faq.md#emulation) for more information.

On Windows, this option can be used to compile for `ARM64` from an Intel
machine, provided the cross-compiling tools are installed.

Options:

- Linux: `x86_64` `i686` `aarch64` `ppc64le` `s390x`
- macOS: `x86_64` `arm64` `universal2`
- Windows: `AMD64` `x86` `ARM64`
- Pyodide: `wasm32`
- `auto`: The default archs for your machine - see the table below.
    - `auto64`: Just the 64-bit auto archs
    - `auto32`: Just the 32-bit auto archs
- `native`: the native arch of the build machine - Matches [`platform.machine()`](https://docs.python.org/3/library/platform.html#platform.machine).
- `all` : expands to all the architectures supported on this OS. You may want
  to use [CIBW_BUILD](#build-skip) with this option to target specific
  architectures via build selectors.

Default: `auto`

| Runner | `native` | `auto` | `auto64` | `auto32` |
|---|---|---|---|---|
| Linux / Intel | `x86_64` | `x86_64` `i686` | `x86_64` | `i686` |
| Windows / Intel | `AMD64` | `AMD64` `x86` | `AMD64` | `x86` |
| Windows / ARM64 | `ARM64` | `ARM64` | `ARM64` | |
| macOS / Intel | `x86_64` | `x86_64` | `x86_64` |  |
| macOS / Apple Silicon | `arm64` | `arm64` | `arm64` |  |

If not listed above, `auto` is the same as `native`.

[setup-qemu-action]: https://github.com/docker/setup-qemu-action
[binfmt]: https://hub.docker.com/r/tonistiigi/binfmt

Platform-specific environment variables are also available:<br/>
 `CIBW_ARCHS_MACOS` | `CIBW_ARCHS_WINDOWS` | `CIBW_ARCHS_LINUX`

This option can also be set using the [command-line option](#command-line)
`--archs`. This option cannot be set in an `overrides` section in `pyproject.toml`.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Build `universal2` and `arm64` wheels on an Intel runner.
    # Note that the `arm64` wheel and the `arm64` part of the `universal2`
    # wheel cannot be tested in this configuration.
    CIBW_ARCHS_MACOS: "x86_64 universal2 arm64"

    # On an Linux Intel runner with qemu installed, build Intel and ARM wheels
    CIBW_ARCHS_LINUX: "auto aarch64"
    ```

    Separate multiple archs with a space.

!!! tab examples "pyproject.toml"

    ```toml
    # Build `universal2` and `arm64` wheels on an Intel runner.
    # Note that the `arm64` wheel and the `arm64` part of the `universal2`
    # wheel cannot be tested in this configuration.
    [tool.cibuildwheel.macos]
    archs = ["x86_64", "universal2", "arm64"]

    # On an Linux Intel runner with qemu installed, build Intel and ARM wheels
    [tool.cibuildwheel.linux]
    archs = ["auto", "aarch64"]
    ```

    It is generally recommended to use the environment variable or
    command-line option for Linux, as selecting archs often depends
    on your specific runner having qemu installed.


###  `CIBW_PROJECT_REQUIRES_PYTHON` {: #requires-python}
> Manually set the Python compatibility of your project

By default, cibuildwheel reads your package's Python compatibility from
`pyproject.toml` following the [project metadata specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/)
or from `setup.cfg`; finally it will try to inspect the AST of `setup.py` for a
simple keyword assignment in a top level function call. If you need to override
this behaviour for some reason, you can use this option.

When setting this option, the syntax is the same as `project.requires-python`,
using 'version specifiers' like `>=3.6`, according to
[PEP440](https://www.python.org/dev/peps/pep-0440/#version-specifiers).

Default: reads your package's Python compatibility from `pyproject.toml`
(`project.requires-python`) or `setup.cfg` (`options.python_requires`) or
`setup.py` `setup(python_requires="...")`. If not found, cibuildwheel assumes
the package is compatible with all versions of Python that it can build.

!!! note
    Rather than using this environment variable, it's recommended you set this value
    statically in a way that your build backend can use it, too. This ensures
    that your package's metadata is correct when published on PyPI. This
    cibuildwheel-specific option is provided as an override, and therefore is only
    available in environment variable form.

      - If you have a `pyproject.toml` containing a `[project]` table, you can
        specify `requires-python` there.

        ```toml
        [project]
        ...
        requires-python = ">=3.6"
        ```

        Note that not all build backends fully support using a `[project]` table yet;
        specifically setuptools just added experimental support in version 61.
        Adding `[project]` to `pyproject.toml` requires all the other supported
        values to be specified there, or to be listed in `dynamic`.

      - If you're using setuptools, [you can set this value in `setup.cfg` (preferred) or `setup.py`](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#python-requirement)
        and cibuildwheel will read it from there.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    CIBW_PROJECT_REQUIRES_PYTHON: ">=3.6"
    ```

###  `CIBW_PRERELEASE_PYTHONS` {: #prerelease-pythons}
> Enable building with pre-release versions of Python if available

During the beta period, when new versions of Python are being tested,
cibuildwheel will often gain early support for beta releases. If you would
like to test wheel building with these versions, you can enable this flag.

!!! caution
    This option is provided for testing purposes only. It is not
    recommended to distribute wheels built when `CIBW_PRERELEASE_PYTHONS` is
    set, such as uploading to PyPI.  Please _do not_ upload these wheels to
    PyPI, as they are not guaranteed to work with the final Python release.
    Once Python is ABI stable and enters the release candidate phase, that
    version of Python will become available without this flag.

Default: Off (0) if Python is available in beta phase. No effect otherwise.

This option can also be set using the [command-line option](#command-line) `--prerelease-pythons`. This option is not available in the `pyproject.toml` config.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Include latest Python beta
    CIBW_PRERELEASE_PYTHONS: True
    ```

## Build customization

### `CIBW_BUILD_FRONTEND` {: #build-frontend}
> Set the tool to use to build, either "pip" (default for now), "build", or "build[uv]"

Options:

- `pip[;args: ...]`
- `build[;args: ...]`

Default: `pip`

Choose which build frontend to use. Can either be "pip", which will run
`python -m pip wheel`, or "build", which will run `python -m build --wheel`.

You can also use "build[uv]", which will use an external [uv][] everywhere
possible, both through `--installer=uv` passed to build, as well as when making
all build and test environments. This will generally speed up cibuildwheel.
Make sure you have an external uv on Windows and macOS, either by
pre-installing it, or installing cibuildwheel with the uv extra,
`cibuildwheel[uv]`. `uv` will not be used for Python 3.6 or Python 3.7. You
cannot use uv currently on Windows for ARM or for musllinux on s390x as
binaries are not provided by uv. Legacy dependencies like setuptools on Python
< 3.12 and pip are not installed if using uv.

Pyodide ignores this setting, as only "build" is supported.

You can specify extra arguments to pass to `pip wheel` or `build` using the
optional `args` option.

!!! tip
    Until v2.0.0, [pip][] was the only way to build wheels, and is still the
    default. However, we expect that at some point in the future, cibuildwheel
    will change the default to [build][], in line with the PyPA's recommendation.
    If you want to try `build` before this, you can use this option.

[pip]: https://pip.pypa.io/en/stable/cli/pip_wheel/
[build]: https://github.com/pypa/build/
[uv]: https://github.com/astral-sh/uv

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Switch to using build
    CIBW_BUILD_FRONTEND: "build"

    # Ensure pip is used even if the default changes in the future
    CIBW_BUILD_FRONTEND: "pip"

    # supply an extra argument to 'pip wheel'
    CIBW_BUILD_FRONTEND: "pip; args: --no-build-isolation"

    # Use uv and build
    CIBW_BUILD_FRONTEND: "build[uv]"

    # Use uv and build with an argument
    CIBW_BUILD_FRONTEND: "build[uv]; args: --no-isolation"
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Switch to using build
    build-frontend = "build"

    # Ensure pip is used even if the default changes in the future
    build-frontend = "pip"

    # supply an extra argument to 'pip wheel'
    build-frontend = { name = "pip", args = ["--no-build-isolation"] }

    # Use uv and build
    build-frontend = "build[uv]"

    # Use uv and build with an argument
    build-frontend = { name = "build[uv]", args = ["--no-isolation"] }
    ```

### `CIBW_CONFIG_SETTINGS` {: #config-settings}
> Specify config-settings for the build backend.

Specify config settings for the build backend. Each space separated
item will be passed via `--config-setting`. In TOML, you can specify
a table of items, including arrays.

!!! tip
    Currently, "build" supports arrays for options, but "pip" only supports
    single values.

Platform-specific environment variables also available:<br/>
`CIBW_CONFIG_SETTINGS_MACOS` | `CIBW_CONFIG_SETTINGS_WINDOWS` | `CIBW_CONFIG_SETTINGS_LINUX` | `CIBW_CONFIG_SETTINGS_PYODIDE`


#### Examples

!!! tab examples "Environment variables"

    ```yaml
    CIBW_CONFIG_SETTINGS: "--build-option=--use-mypyc"
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.config-settings]
    --build-option = "--use-mypyc"
    ```


### `CIBW_ENVIRONMENT` {: #environment}
> Set environment variables

A list of environment variables to set during the build and test phases. Bash syntax should be used, even on Windows.

You must use this variable to pass variables to Linux builds, since they execute in a container. It also works for the other platforms.

You can use `$PATH` syntax to insert other variables, or the `$(pwd)` syntax to insert the output of other shell commands.

To specify more than one environment variable, separate the assignments by spaces.

Platform-specific environment variables are also available:<br/>
`CIBW_ENVIRONMENT_MACOS` | `CIBW_ENVIRONMENT_WINDOWS` | `CIBW_ENVIRONMENT_LINUX` | `CIBW_ENVIRONMENT_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Set some compiler flags
    CIBW_ENVIRONMENT: CFLAGS='-g -Wall' CXXFLAGS='-Wall'

    # Append a directory to the PATH variable (this is expanded in the build environment)
    CIBW_ENVIRONMENT: PATH=$PATH:/usr/local/bin

    # Prepend a directory containing spaces on Windows.
    CIBW_ENVIRONMENT_WINDOWS: >
      PATH="C:\\Program Files\\PostgreSQL\\13\\bin;$PATH"

    # Set BUILD_TIME to the output of the `date` command
    CIBW_ENVIRONMENT: BUILD_TIME="$(date)"

    # Supply options to `pip` to affect how it downloads dependencies
    CIBW_ENVIRONMENT: PIP_EXTRA_INDEX_URL=https://pypi.myorg.com/simple

    # Any pip command-line options can be set using the PIP_ prefix
    # https://pip.pypa.io/en/stable/topics/configuration/#environment-variables
    CIBW_ENVIRONMENT: PIP_GLOBAL_OPTION="build_ext -j4"

    # Set two flags on linux only
    CIBW_ENVIRONMENT_LINUX: BUILD_TIME="$(date)" SAMPLE_TEXT="sample text"
    ```

    Separate multiple values with a space.

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Set some compiler flags
    environment = "CFLAGS='-g -Wall' CXXFLAGS='-Wall'"

    # Set some compiler flags using a TOML table
    environment = { CFLAGS="-g -Wall", CXXFLAGS="-Wall" }

    # Append a directory to the PATH variable (this is expanded in the build environment)
    environment = { PATH="$PATH:/usr/local/bin" }

    # Prepend a directory containing spaces on Windows.
    [tool.cibuildwheel.windows]
    environment = { PATH='C:\\Program Files\\PostgreSQL\\13\\bin;$PATH' }

    # Set BUILD_TIME to the output of the `date` command
    environment = { BUILD_TIME="$(date)" }

    # Supply options to `pip` to affect how it downloads dependencies
    environment = { PIP_EXTRA_INDEX_URL="https://pypi.myorg.com/simple" }

    # Any pip command-line option can be set using the PIP_ prefix
    # https://pip.pypa.io/en/stable/topics/configuration/#environment-variables
    environment = { PIP_GLOBAL_OPTION="build_ext -j4" }

    # Set two flags on linux only
    [tool.cibuildwheel.linux]
    environment = { BUILD_TIME="$(date)", SAMPLE_TEXT="sample text" }

    # Alternate form with out-of-line table for setting a few values
    [tool.cibuildwheel.linux.environment]
    BUILD_TIME = "$(date)"
    SAMPLE_TEXT = "sample text"
    ```

    In configuration mode, you can use a [TOML][] table instead of a raw string as shown above.

!!! note
    cibuildwheel always defines the environment variable `CIBUILDWHEEL=1`. This can be useful for [building wheels with optional extensions](faq.md#building-packages-with-optional-c-extensions).

!!! note
    To do its work, cibuildwheel sets the variables `VIRTUALENV_PIP`, `DIST_EXTRA_CONFIG`, `SETUPTOOLS_EXT_SUFFIX`, `PIP_DISABLE_PIP_VERSION_CHECK`, `PIP_ROOT_USER_ACTION`, and it extends the variables `PATH` and `PIP_CONSTRAINT`. Your assignments to these options might be replaced or extended.

### `CIBW_ENVIRONMENT_PASS_LINUX` {: #environment-pass}
> Set environment variables on the host to pass-through to the container.

A list of environment variables to pass into the linux container during each build and test. It has no effect on the other platforms, which can already access all environment variables directly.

To specify more than one environment variable, separate the variable names by spaces.

!!! note
    cibuildwheel automatically passes the environment variable [`SOURCE_DATE_EPOCH`](https://reproducible-builds.org/docs/source-date-epoch/) if defined.

#### Examples

!!! tab examples "Environment passthrough"

    ```yaml
    # Export a variable
    CIBW_ENVIRONMENT_PASS_LINUX: CFLAGS

    # Set two flags variables
    CIBW_ENVIRONMENT_PASS_LINUX: BUILD_TIME SAMPLE_TEXT
    ```

    Separate multiple values with a space.

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.linux]

    # Export a variable
    environment-pass = ["CFLAGS"]

    # Set two flags variables
    environment-pass = ["BUILD_TIME", "SAMPLE_TEXT"]
    ```

    In configuration mode, you can use a [TOML][] list instead of a raw string as shown above.

### `CIBW_BEFORE_ALL` {: #before-all}
> Execute a shell command on the build system before any wheels are built.

Shell command that runs before any builds are run, to build or install parts that do not depend on the specific version of Python.

This option is very useful for the Linux build, where builds take place in isolated containers managed by cibuildwheel. This command will run inside the container before the wheel builds start. Note, if you're building both `x86_64` and `i686` wheels (the default), your build uses two different container images. In that case, this command will execute twice - once per build container.

The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

On Windows and macOS, the version of Python available inside `CIBW_BEFORE_ALL` is whatever is available on the host machine. On Linux, a modern Python version is available on PATH.

This option has special behavior in the overrides section in `pyproject.toml`.
On linux, overriding it triggers a new container launch. It cannot be overridden
on macOS and Windows.

Platform-specific environment variables also available:<br/>
`CIBW_BEFORE_ALL_MACOS` | `CIBW_BEFORE_ALL_WINDOWS` | `CIBW_BEFORE_ALL_LINUX` | `CIBW_BEFORE_ALL_PYODIDE`

!!! note

    This command is executed in a different Python environment from the builds themselves. So you can't `pip install` a Python dependency in CIBW_BEFORE_ALL and use it in the build. Instead, look at [`CIBW_BEFORE_BUILD`](#before-build), or, if your project uses pyproject.toml, the [build-system.requires](https://peps.python.org/pep-0518/#build-system-table) field.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Build third party library
    CIBW_BEFORE_ALL: make -C third_party_lib

    # Install system library
    CIBW_BEFORE_ALL_LINUX: yum install -y libffi-devel

    # Chain multiple commands using && and > in a YAML file, like:
    CIBW_BEFORE_ALL: >
      yum install bzip2 -y &&
      make third_party
    ```

    For multiline commands, see the last example. The character `>` means that
    whitespace is collapsed to a single line, and '&&' between each command
    ensures that errors are not ignored. [Further reading on multiline YAML
    here.](https://yaml-multiline.info).

!!! tab examples "pyproject.toml"

    ```toml
    # Build third party library
    [tool.cibuildwheel]
    before-all = "make -C third_party_lib"

    # Install system library
    [tool.cibuildwheel.linux]
    before-all = "yum install -y libffi-devel"

    # Run multiple commands using an array
    before-all = [
      "yum install bzip2 -y",
      "make third_party",
    ]
    ```

    In configuration files, you can use a TOML array, and each line will be run sequentially - joined with `&&`.

Note that manylinux_2_24 builds occur inside a Debian9 docker, where
manylinux2010 and manylinux2014 builds occur inside a CentOS one. So for
`manylinux_2_24` the `CIBW_BEFORE_ALL_LINUX` command must use `apt-get -y`
instead.

### `CIBW_BEFORE_BUILD` {: #before-build}
> Execute a shell command preparing each wheel's build

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), instead of using this command, we recommend adding requirements to a `pyproject.toml` file's `build-system.requires` array instead. This is reproducible, and users who do not get your wheels (such as Alpine or ClearLinux users) will still benefit.

The active Python binary can be accessed using `python`, and pip with `pip`; cibuildwheel makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX` | `CIBW_BEFORE_BUILD_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Install something required for the build (you might want to use pyproject.toml instead)
    CIBW_BEFORE_BUILD: pip install pybind11

    # Chain commands using &&
    CIBW_BEFORE_BUILD_LINUX: python scripts/install-deps.py && make clean

    # Run a script that's inside your project
    CIBW_BEFORE_BUILD: bash scripts/prepare_for_build.sh

    # If cibuildwheel is called with a package_dir argument, it's available as {package}
    CIBW_BEFORE_BUILD: "{package}/script/prepare_for_build.sh"
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]

    # Install something required for the build
    # (you might want to use build-system.requires instead)
    before-build = "pip install pybind11"

    # Chain commands using && or make an array.
    before-build = "python scripts/install-deps.py && make clean"
    before-build = [
        "python scripts/install-deps.py",
        "make clean",
    ]

    # Run a script that's inside your project
    before-build = "bash scripts/prepare_for_build.sh"

    # If cibuildwheel is called with a package_dir argument, it's available as {package}
    before-build = "{package}/script/prepare_for_build.sh"
    ```

    In configuration mode, you can use a array, and the items will be joined with `&&`. In TOML, using a single-quote string will avoid escapes - useful for
    Windows paths.

!!! note
    If you need Python dependencies installed for the build, we recommend using
    `pyproject.toml`'s `build-system.requires` instead. This is an example
    `pyproject.toml` file:

        [build-system]
        requires = [
            "setuptools>=42",
            "Cython",
            "numpy==1.13.3; python_version<'3.5'",
            "oldest-supported-numpy; python_version>='3.5'",
        ]

        build-backend = "setuptools.build_meta"

    This [PEP 517][]/[PEP 518][] style build allows you to completely control
    the build environment in cibuildwheel, [PyPA-build][], and pip, doesn't
    force downstream users to install anything they don't need, and lets you do
    more complex pinning (Cython, for example, requires a wheel to be built
    with an equal or earlier version of NumPy; pinning in this way is the only
    way to ensure your module works on all available NumPy versions).

    [PyPA-build]: https://pypa-build.readthedocs.io/en/latest/
    [PEP 517]: https://www.python.org/dev/peps/pep-0517/
    [PEP 518]: https://www.python.org/dev/peps/pep-0517/


### `CIBW_REPAIR_WHEEL_COMMAND` {: #repair-wheel-command}
> Execute a shell command to repair each built wheel

Default:

- on Linux: `'auditwheel repair -w {dest_dir} {wheel}'`
- on macOS: `'delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}'`
- on Windows: `''`
- on Pyodide: `''`

A shell command to repair a built wheel by copying external library dependencies into the wheel tree and relinking them.
The command is run on each built wheel (except for pure Python ones) before testing it.

The following placeholders must be used inside the command and will be replaced by cibuildwheel:

- `{wheel}` for the absolute path to the built wheel
- `{dest_dir}` for the absolute path of the directory where to create the repaired wheel
- `{delocate_archs}` (macOS only) comma-separated list of architectures in the wheel.

The command is run in a shell, so you can run multiple commands like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
`CIBW_REPAIR_WHEEL_COMMAND_MACOS` | `CIBW_REPAIR_WHEEL_COMMAND_WINDOWS` | `CIBW_REPAIR_WHEEL_COMMAND_LINUX` | `CIBW_REPAIR_WHEEL_COMMAND_PYODIDE`

!!! tip
    cibuildwheel doesn't yet ship a default repair command for Windows.

    **If that's an issue for you, check out [delvewheel]** - a new package that aims to do the same as auditwheel or delocate for Windows.

    Because delvewheel is still relatively early-stage, cibuildwheel does not yet run it by default. However, we'd recommend giving it a try! See the examples below for usage.

    [Delvewheel]: https://github.com/adang1345/delvewheel

!!! tip
    When using `--platform pyodide`, `pyodide build` is used to do the build,
    which already uses `auditwheel-emscripten` to repair the wheel, so the default
    repair command is empty. If there is a way to do this in two steps in the future,
    this could change.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Use delvewheel on windows
    CIBW_BEFORE_BUILD_WINDOWS: "pip install delvewheel"
    CIBW_REPAIR_WHEEL_COMMAND_WINDOWS: "delvewheel repair -w {dest_dir} {wheel}"

    # Don't repair macOS wheels
    CIBW_REPAIR_WHEEL_COMMAND_MACOS: ""

    # Pass the `--lib-sdir .` flag to auditwheel on Linux
    CIBW_REPAIR_WHEEL_COMMAND_LINUX: "auditwheel repair --lib-sdir . -w {dest_dir} {wheel}"

    # Multi-line example - use && to join on all platforms
    CIBW_REPAIR_WHEEL_COMMAND: >
      python scripts/repair_wheel.py -w {dest_dir} {wheel} &&
      python scripts/check_repaired_wheel.py -w {dest_dir} {wheel}

    # Use abi3audit to catch issues with Limited API wheels
    CIBW_REPAIR_WHEEL_COMMAND_LINUX: >
      auditwheel repair -w {dest_dir} {wheel} &&
      pipx run abi3audit --strict --report {wheel}
    CIBW_REPAIR_WHEEL_COMMAND_MACOS: >
      delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel} &&
      pipx run abi3audit --strict --report {wheel}
    CIBW_REPAIR_WHEEL_COMMAND_WINDOWS: >
      pipx run abi3audit --strict --report {wheel}
    ```

!!! tab examples "pyproject.toml"

    ```toml
    # Use delvewheel on windows
    [tool.cibuildwheel.windows]
    before-build = "pip install delvewheel"
    repair-wheel-command = "delvewheel repair -w {dest_dir} {wheel}"

    # Don't repair macOS wheels
    [tool.cibuildwheel.macos]
    repair-wheel-command = ""

    # Pass the `--lib-sdir .` flag to auditwheel on Linux
    [tool.cibuildwheel.linux]
    repair-wheel-command = "auditwheel repair --lib-sdir . -w {dest_dir} {wheel}"

    # Multi-line example
    [tool.cibuildwheel]
    repair-wheel-command = [
      'python scripts/repair_wheel.py -w {dest_dir} {wheel}',
      'python scripts/check_repaired_wheel.py -w {dest_dir} {wheel}',
    ]

    # Use abi3audit to catch issues with Limited API wheels
    [tool.cibuildwheel.linux]
    repair-wheel-command = [
      "auditwheel repair -w {dest_dir} {wheel}",
      "pipx run abi3audit --strict --report {wheel}",
    ]
    [tool.cibuildwheel.macos]
    repair-wheel-command = [
      "delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}",
      "pipx run abi3audit --strict --report {wheel}",
    ]
    [tool.cibuildwheel.windows]
    repair-wheel-command = "pipx run abi3audit --strict --report {wheel}"
    ```

    In configuration mode, you can use an inline array, and the items will be joined with `&&`.


<div class="link-target" id="manylinux-image"></div>

### `CIBW_MANYLINUX_*_IMAGE`, `CIBW_MUSLLINUX_*_IMAGE` {: #linux-image}
> Specify alternative manylinux / musllinux container images

The available options are (default value):

- `CIBW_MANYLINUX_X86_64_IMAGE` ([`quay.io/pypa/manylinux2014_x86_64`](https://quay.io/pypa/manylinux2014_x86_64))
- `CIBW_MANYLINUX_I686_IMAGE` ([`quay.io/pypa/manylinux2014_i686`](https://quay.io/pypa/manylinux2014_i686))
- `CIBW_MANYLINUX_PYPY_X86_64_IMAGE` ([`quay.io/pypa/manylinux2014_x86_64`](https://quay.io/pypa/manylinux2014_x86_64))
- `CIBW_MANYLINUX_AARCH64_IMAGE` ([`quay.io/pypa/manylinux2014_aarch64`](https://quay.io/pypa/manylinux2014_aarch64))
- `CIBW_MANYLINUX_PPC64LE_IMAGE` ([`quay.io/pypa/manylinux2014_ppc64le`](https://quay.io/pypa/manylinux2014_ppc64le))
- `CIBW_MANYLINUX_S390X_IMAGE` ([`quay.io/pypa/manylinux2014_s390x`](https://quay.io/pypa/manylinux2014_s390x))
- `CIBW_MANYLINUX_PYPY_AARCH64_IMAGE` ([`quay.io/pypa/manylinux2014_aarch64`](https://quay.io/pypa/manylinux2014_aarch64))
- `CIBW_MANYLINUX_PYPY_I686_IMAGE` ([`quay.io/pypa/manylinux2014_i686`](https://quay.io/pypa/manylinux2014_i686))
- `CIBW_MUSLLINUX_X86_64_IMAGE` ([`quay.io/pypa/musllinux_1_2_x86_64`](https://quay.io/pypa/musllinux_1_2_x86_64))
- `CIBW_MUSLLINUX_I686_IMAGE` ([`quay.io/pypa/musllinux_1_2_i686`](https://quay.io/pypa/musllinux_1_2_i686))
- `CIBW_MUSLLINUX_AARCH64_IMAGE` ([`quay.io/pypa/musllinux_1_2_aarch64`](https://quay.io/pypa/musllinux_1_2_aarch64))
- `CIBW_MUSLLINUX_PPC64LE_IMAGE` ([`quay.io/pypa/musllinux_1_2_ppc64le`](https://quay.io/pypa/musllinux_1_2_ppc64le))
- `CIBW_MUSLLINUX_S390X_IMAGE` ([`quay.io/pypa/musllinux_1_2_s390x`](https://quay.io/pypa/musllinux_1_2_s390x))

Set an alternative Docker image to be used for building [manylinux / musllinux](https://github.com/pypa/manylinux) wheels.

For `CIBW_MANYLINUX_*_IMAGE`, the value of this option can either be set to `manylinux1`, `manylinux2010`, `manylinux2014`, `manylinux_2_24` or `manylinux_2_28` to use a pinned version of the [official manylinux images](https://github.com/pypa/manylinux). Alternatively, set these options to any other valid Docker image name. For PyPy, the `manylinux1` image is not available. For architectures other
than x86 (x86\_64 and i686) `manylinux2014`, `manylinux_2_24` or `manylinux_2_28` must be used, because the first version of the manylinux specification that supports additional architectures is `manylinux2014`. `manylinux_2_28` is not supported for `i686` architecture.

For `CIBW_MUSLLINUX_*_IMAGE`, the value of this option can either be set to `musllinux_1_1` or `musllinux_1_2` to use a pinned version of the [official musllinux images](https://github.com/pypa/musllinux). Alternatively, set these options to any other valid Docker image name.

If this option is blank, it will fall though to the next available definition (environment variable -> pyproject.toml -> default).

If setting a custom image, you'll need to make sure it can be used in the same way as the default images: all necessary Python and pip versions need to be present in `/opt/python/`, and the auditwheel tool needs to be present for cibuildwheel to work. Apart from that, the architecture and relevant shared system libraries need to be compatible to the relevant standard to produce valid manylinux1/manylinux2010/manylinux2014/manylinux_2_24/manylinux_2_28/musllinux_1_1/musllinux_1_2 wheels (see [pypa/manylinux on GitHub](https://github.com/pypa/manylinux), [PEP 513](https://www.python.org/dev/peps/pep-0513/), [PEP 571](https://www.python.org/dev/peps/pep-0571/), [PEP 599](https://www.python.org/dev/peps/pep-0599/), [PEP 600](https://www.python.org/dev/peps/pep-0600/) and [PEP 656](https://www.python.org/dev/peps/pep-0656/) for more details).

Auditwheel detects the version of the manylinux / musllinux standard in the image through the `AUDITWHEEL_PLAT` environment variable, as cibuildwheel has no way of detecting the correct `--plat` command line argument to pass to auditwheel for a custom image. If a custom image does not correctly set this `AUDITWHEEL_PLAT` environment variable, the `CIBW_ENVIRONMENT` option can be used to do so (e.g., `CIBW_ENVIRONMENT='AUDITWHEEL_PLAT="manylinux2010_$(uname -m)"'`).

#### Examples


!!! tab examples "Environment variables"

    ```yaml
    # Build using the manylinux1 image to ensure manylinux1 wheels are produced
    # Not setting PyPy to manylinux1, since there is no manylinux1 PyPy image.
    CIBW_MANYLINUX_X86_64_IMAGE: manylinux1
    CIBW_MANYLINUX_I686_IMAGE: manylinux1

    # Build using the manylinux2014 image
    CIBW_MANYLINUX_X86_64_IMAGE: manylinux2014
    CIBW_MANYLINUX_I686_IMAGE: manylinux2014
    CIBW_MANYLINUX_PYPY_X86_64_IMAGE: manylinux2014
    CIBW_MANYLINUX_PYPY_I686_IMAGE: manylinux2014

    # Build using the latest manylinux2014 release, instead of the cibuildwheel
    # pinned version
    CIBW_MANYLINUX_X86_64_IMAGE: quay.io/pypa/manylinux2014_x86_64:latest
    CIBW_MANYLINUX_I686_IMAGE: quay.io/pypa/manylinux2014_i686:latest
    CIBW_MANYLINUX_PYPY_X86_64_IMAGE: quay.io/pypa/manylinux2014_x86_64:latest
    CIBW_MANYLINUX_PYPY_I686_IMAGE: quay.io/pypa/manylinux2014_i686:latest

    # Build using a different image from the docker registry
    CIBW_MANYLINUX_X86_64_IMAGE: dockcross/manylinux-x64
    CIBW_MANYLINUX_I686_IMAGE: dockcross/manylinux-x86

    # Build musllinux wheels using the musllinux_1_1 image
    CIBW_MUSLLINUX_X86_64_IMAGE: musllinux_1_1
    CIBW_MUSLLINUX_I686_IMAGE: musllinux_1_1
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Build using the manylinux1 image to ensure manylinux1 wheels are produced
    # Not setting PyPy to manylinux1, since there is no manylinux1 PyPy image.
    manylinux-x86_64-image = "manylinux1"
    manylinux-i686-image = "manylinux1"

    # Build using the manylinux2014 image
    manylinux-x86_64-image = "manylinux2014"
    manylinux-i686-image = "manylinux2014"
    manylinux-pypy_x86_64-image = "manylinux2014"
    manylinux-pypy_i686-image = "manylinux2014"

    # Build using the latest manylinux2010 release, instead of the cibuildwheel
    # pinned version
    manylinux-x86_64-image = "quay.io/pypa/manylinux2010_x86_64:latest"
    manylinux-i686-image = "quay.io/pypa/manylinux2010_i686:latest"
    manylinux-pypy_x86_64-image = "quay.io/pypa/manylinux2010_x86_64:latest"
    manylinux-pypy_i686-image = "quay.io/pypa/manylinux2010_i686:latest"

    # Build using a different image from the docker registry
    manylinux-x86_64-image = "dockcross/manylinux-x64"
    manylinux-i686-image = "dockcross/manylinux-x86"

    # Build musllinux wheels using the musllinux_1_1 image
    musllinux-x86_64-image = "musllinux_1_1"
    musllinux-i686-image = "musllinux_1_1"
    ```

    Like any other option, these can be placed in `[tool.cibuildwheel.linux]`
    if you prefer; they have no effect on `macos` and `windows`.


### `CIBW_CONTAINER_ENGINE` {: #container-engine}
> Specify the container engine to use when building Linux wheels

Options:

- `docker[;create_args: ...][;disable_host_mount: true/false]`
- `podman[;create_args: ...][;disable_host_mount: true/false]`

Default: `docker`

Set the container engine to use. Docker is the default, or you can switch to
[Podman](https://podman.io/). To use Docker, you need to have a Docker daemon
running and `docker` available on PATH. To use Podman, it needs to be
installed and `podman` available on PATH.

Options can be supplied after the name.

| Option name | Description
|---|---
| `create_args` | Space-separated strings, which are passed to the container engine on the command line when it's creating the container. If you want to include spaces inside a parameter, use shell-style quoting.
| `disable_host_mount` | By default, cibuildwheel will mount the root of the host filesystem as a volume at `/host` in the container. To disable the host mount, pass `true` to this option.


!!! tip

    While most users will stick with Docker, Podman is available in different
    contexts - for example, it can be run inside a Docker container, or without
    root access. Thanks to the [OCI], images are compatible between engines, so
    you can still use the regular manylinux/musllinux containers.

[OCI]: https://opencontainers.org/

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # use podman instead of docker
    CIBW_CONTAINER_ENGINE: podman

    # pass command line options to 'docker create'
    CIBW_CONTAINER_ENGINE: "docker; create_args: --gpus all"

    # disable the /host mount
    CIBW_CONTAINER_ENGINE: "docker; disable_host_mount: true"
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # use podman instead of docker
    container-engine = "podman"

    # pass command line options to 'docker create'
    container-engine = { name = "docker", create-args = ["--gpus", "all"]}

    # disable the /host mount
    container-engine = { name = "docker", disable-host-mount = true }
    ```


### `CIBW_DEPENDENCY_VERSIONS` {: #dependency-versions}
> Specify how cibuildwheel controls the versions of the tools it uses

Options: `pinned` `latest` `<your constraints file>`

Default: `pinned`

If `CIBW_DEPENDENCY_VERSIONS` is `pinned`, cibuildwheel uses versions of tools
like `pip`, `setuptools`, `virtualenv` that were pinned with that release of
cibuildwheel. This represents a known-good set of dependencies, and is
recommended for build repeatability.

If set to `latest`, cibuildwheel will use the latest of these packages that
are available on PyPI. This might be preferable if these packages have bug
fixes that can't wait for a new cibuildwheel release.

To control the versions of dependencies yourself, you can supply a [pip
constraints](https://pip.pypa.io/en/stable/user_guide/#constraints-files) file
here and it will be used instead.

!!! note
    If you need different dependencies for each python version, provide them
    in the same folder with a `-pythonXY` suffix. e.g. if your
    `CIBW_DEPENDENCY_VERSIONS=./constraints.txt`, cibuildwheel will use
    `./constraints-python37.txt` on Python 3.7, or fallback to
    `./constraints.txt` if that's not found.

Platform-specific environment variables are also available:<br/>
`CIBW_DEPENDENCY_VERSIONS_MACOS` | `CIBW_DEPENDENCY_VERSIONS_WINDOWS` | `CIBW_DEPENDENCY_VERSIONS_PYODIDE`

!!! note
    This option does not affect the tools used on the Linux build - those versions
    are bundled with the manylinux/musllinux image that cibuildwheel uses. To change
    dependency versions on Linux, use the [CIBW_MANYLINUX_* / CIBW_MUSLLINUX_*](#linux-image)
    options.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Use tools versions that are bundled with cibuildwheel (this is the default)
    CIBW_DEPENDENCY_VERSIONS: pinned

    # Use the latest versions available on PyPI
    CIBW_DEPENDENCY_VERSIONS: latest

    # Use your own pip constraints file
    CIBW_DEPENDENCY_VERSIONS: ./constraints.txt
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Use tools versions that are bundled with cibuildwheel (this is the default)
    dependency-versions = "pinned"

    # Use the latest versions available on PyPI
    dependency-versions = "latest"

    # Use your own pip constraints file
    dependency-versions = "./constraints.txt"
    ```


## Testing

### `CIBW_TEST_COMMAND` {: #test-command}
> Execute a shell command to test each built wheel

Shell command to run tests after the build. The wheel will be installed
automatically and available for import from the tests. To ensure the wheel is
imported by your tests (instead of your source copy), **tests are not run from
your project directory**. Use the placeholders `{project}` and `{package}` when
specifying paths in your project. If this variable is not set, your wheel will
not be installed after building.

- `{project}` is an absolute path to the project root - the working directory
  where cibuildwheel was called.
- `{package}` is the path to the package being built - the `package_dir`
  argument supplied to cibuildwheel on the command line.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX` | `CIBW_TEST_COMMAND_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Run the project tests against the installed wheel using `nose`
    CIBW_TEST_COMMAND: nosetests {project}/tests

    # Run the package tests using `pytest`
    CIBW_TEST_COMMAND: pytest {package}/tests

    # Trigger an install of the package, but run nothing of note
    CIBW_TEST_COMMAND: "echo Wheel installed"

    # Multi-line example - join with && on all platforms
    CIBW_TEST_COMMAND: >
      pytest {package}/tests &&
      python {package}/test.py
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Run the project tests against the installed wheel using `nose`
    test-command = "nosetests {project}/tests"

    # Run the package tests using `pytest`
    test-command = "pytest {package}/tests"

    # Trigger an install of the package, but run nothing of note
    test-command = "echo Wheel installed"

    # Multiline example
    test-command = [
      "pytest {package}/tests",
      "python {package}/test.py",
    ]
    ```

    In configuration files, you can use an array, and the items will be joined with `&&`.

!!! note

    It isn't recommended to `cd` to your project directory before running tests,
    because Python might resolve `import yourpackage` relative to the working dir,
    and we want to test the wheel you just built. However, if you're sure that's not
    an issue for you and your workflow requires it, on Windows you should do `cd /d`,
    because the CWD and project dir might be on different drives.

### `CIBW_BEFORE_TEST` {: #before-test}
> Execute a shell command before testing each wheel

A shell command to run in **each** test virtual environment, before your wheel is installed and tested. This is useful if you need to install a non-pip package, invoke pip with different environment variables,
or perform a multi-step pip installation (e.g. installing scikit-build or Cython before installing test package).

The active Python binary can be accessed using `python`, and pip with `pip`; cibuildwheel makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
 `CIBW_BEFORE_TEST_MACOS` | `CIBW_BEFORE_TEST_WINDOWS` | `CIBW_BEFORE_TEST_LINUX` | `CIBW_BEFORE_TEST_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Install test dependencies with overwritten environment variables.
    CIBW_BEFORE_TEST: CC=gcc CXX=g++ pip install -r requirements.txt

    # Chain commands using &&
    CIBW_BEFORE_TEST: rm -rf ./data/cache && mkdir -p ./data/cache

    # Install non pip python package
    CIBW_BEFORE_TEST: >
      cd some_dir &&
      ./configure &&
      make &&
      make install

    # Install python packages that are required to install test dependencies
    CIBW_BEFORE_TEST: pip install cmake scikit-build
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Install test dependencies with overwritten environment variables.
    before-test = "CC=gcc CXX=g++ pip install -r requirements.txt"

    # Chain commands using && or using an array
    before-test = "rm -rf ./data/cache && mkdir -p ./data/cache"
    before-test = [
        "rm -rf ./data/cache",
        "mkdir -p ./data/cache",
    ]

    # Install non pip python package
    before-test = [
        "cd some_dir",
        "./configure",
        "make",
        "make install",
    ]

    # Install python packages that are required to install test dependencies
    [tool.cibuildwheel]
    before-test = "pip install cmake scikit-build"
    ```

    In configuration files, you can use an array, and the items will be joined with `&&`.


### `CIBW_TEST_REQUIRES` {: #test-requires}
> Install Python dependencies before running the tests

Space-separated list of dependencies required for running the tests.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX` | `CIBW_TEST_REQUIRES_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Install pytest before running CIBW_TEST_COMMAND
    CIBW_TEST_REQUIRES: pytest

    # Install specific versions of test dependencies
    CIBW_TEST_REQUIRES: nose==1.3.7 moto==0.4.31
    ```

!!! tab examples "pyproject.toml"

    ```toml
    # Install pytest before running CIBW_TEST_COMMAND
    [tool.cibuildwheel]
    test-requires = "pytest"

    # Install specific versions of test dependencies
    [tool.cibuildwheel]
    test-requires = ["nose==1.3.7", "moto==0.4.31"]
    ```

    In configuration files, you can use an array, and the items will be joined with a space.


### `CIBW_TEST_EXTRAS` {: #test-extras}
> Install your wheel for testing using `extras_require`

List of
[extras_require](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#declaring-required-dependency)
options that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`CIBW_TEST_REQUIRES` if they are already defined in `pyproject.toml`,
`setup.cfg` or `setup.py`.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_EXTRAS_MACOS` | `CIBW_TEST_EXTRAS_WINDOWS` | `CIBW_TEST_EXTRAS_LINUX` | `CIBW_TEST_EXTRAS_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`
    CIBW_TEST_EXTRAS: "test,qt"
    ```

    Separate multiple items with a comma.

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`
    test-extras = ["test", "qt"]
    ```

    In configuration files, you can use an inline array, and the items will be joined with a comma.

### `CIBW_TEST_SKIP` {: #test-skip}
> Skip running tests on some builds

This will skip testing on any identifiers that match the given skip patterns (see [`CIBW_SKIP`](#build-skip)). This can be used to mask out tests for wheels that have missing dependencies upstream that are slow or hard to build, or to skip slow tests on emulated architectures.

With macOS `universal2` wheels, you can also skip the individual archs inside the wheel using an `:arch` suffix. For example, `cp39-macosx_universal2:x86_64` or `cp39-macosx_universal2:arm64`.

This option is not supported in the overrides section in `pyproject.toml`.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Will avoid testing on emulated architectures
    CIBW_TEST_SKIP: "*-*linux_{aarch64,ppc64le,s390x}"

    # Skip trying to test arm64 builds on Intel Macs
    CIBW_TEST_SKIP: "*-macosx_arm64 *-macosx_universal2:arm64"
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Will avoid testing on emulated architectures
    test-skip = "*-*linux_{aarch64,ppc64le,s390x}"

    # Skip trying to test arm64 builds on Intel Macs
    test-skip = "*-macosx_arm64 *-macosx_universal2:arm64"
    ```

## Debugging

### `CIBW_DEBUG_KEEP_CONTAINER`

Enable this flag to keep the container around for inspection after a build. This
option is provided for debugging purposes only.

Default: Off (0).

!!! caution
    This option can only be set as environment variable on the host machine

#### Examples

```shell
export CIBW_DEBUG_KEEP_CONTAINER=TRUE
```

### `CIBW_DEBUG_TRACEBACK`
> Print full traceback when errors occur.

Print a full traceback for the cibuildwheel process when errors occur. This
option is provided for debugging cibuildwheel.

This option can also be set using the [command-line option](#command-line) `--debug-traceback`.

#### Examples

```shell
export CIBW_DEBUG_TRACEBACK=TRUE
```

### `CIBW_BUILD_VERBOSITY` {: #build-verbosity}
> Increase/decrease the output of pip wheel

A number from 1 to 3 to increase the level of verbosity (corresponding to invoking pip with `-v`, `-vv`, and `-vvv`), between -1 and -3 (`-q`, `-qq`, and `-qqq`), or just 0 (default verbosity). These flags are useful while debugging a build when the output of the actual build invoked by `pip wheel` is required. Has no effect on the `build` backend, which produces verbose output by default.

Platform-specific environment variables are also available:<br/>
`CIBW_BUILD_VERBOSITY_MACOS` | `CIBW_BUILD_VERBOSITY_WINDOWS` | `CIBW_BUILD_VERBOSITY_LINUX` | `CIBW_BUILD_VERBOSITY_PYODIDE`

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Increase pip debugging output
    CIBW_BUILD_VERBOSITY: 1
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Increase pip debugging output
    build-verbosity = 1
    ```


## Command line {: #command-line}

### Options

```text
« subprocess_run("cibuildwheel", "--help") »
```

### Return codes

cibuildwheel exits 0 on success, or >0 if an error occurs.

Specific error codes are defined:

- 2 means a configuration error
- 3 means no builds are selected (and --allow-empty wasn't passed)
- 4 means you specified an option that has been deprecated.


## Placeholders

Some options support placeholders, like `{project}`, `{package}` or `{wheel}`, that are substituted by cibuildwheel before they are used. If, for some reason, you need to write the literal name of a placeholder, e.g. literally `{project}` in a command that would ordinarily substitute `{project}`, prefix it with a hash character - `#{project}`. This is only necessary in commands where the specific string between the curly brackets would be substituted - otherwise, strings not modified.

<style>
  .options-toc {
    display: grid;
    grid-template-columns: fit-content(20%) 1fr;
    grid-gap: 16px 32px;
    gap: 16px 32px;
    font-size: 90%;
    margin-bottom: 28px;
    margin-top: 28px;
    overflow-x: auto;
  }
  @media screen and (max-width: 768px) {
    .options-toc {
      grid-gap: 1em 0.5em;
      gap: 1em 0.5em;
    }
  }
  .options-toc .header {
    grid-column: 1 / 3;
    font-weight: bold;
  }
  .options-toc .header:first-child {
    margin-top: 0;
  }
  .options-toc a.option {
    display: block;
    margin-bottom: 5px;
  }
  h3 code {
    font-size: 100%;
  }
</style>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    // gather the options data
    var options = {}
    var headers = []

    $('.rst-content h3')
      .filter(function (i, el) {
        return !!$(el).text().match(/(^([A-Z0-9, _*]| and )+)¶$/);
      })
      .each(function (i, el) {
        var optionName = $(el).text().replace('¶', '');
        var description = $(el).next('blockquote').text()
        var header = $(el).prevAll('h2').first().text().replace('¶', '')
        var id = el.id;

        if (options[header] === undefined) {
          options[header] = [];
          headers.push(header);
        }
        console.log(optionName, description, header);

        options[header].push({name: optionName, description, id});
      });

    // write the table of contents

    var tocTable = $('.options-toc');

    for (var i = 0; i < headers.length; i += 1) {
      var header = headers[i];
      var headerOptions = options[header];

      $('<div class="header">').text(header).appendTo(tocTable);

      for (var j = 0; j < headerOptions.length; j += 1) {
        var option = headerOptions[j];

        var optionNames = option.name.split(', ')

        $('<div class="name">')
          .append($.map(optionNames, function (name) {
            return $('<a class="option">')
              .append(
                $('<code>').text(name)
              )
              .attr('href', '#'+option.id)
            }
          ))
          .appendTo(tocTable);
        $('<div class="description">')
          .text(option.description)
          .appendTo(tocTable);
      }
    }

    // write the markdown table for the README

    var markdown = ''

    markdown += '|   | Option | Description |\n'
    markdown += '|---|--------|-------------|\n'

    var prevHeader = null

    for (var i = 0; i < headers.length; i += 1) {
      var header = headers[i];
      var headerOptions = options[header];
      for (var j = 0; j < headerOptions.length; j += 1) {
        var option = headerOptions[j];

        if (j == 0) {
          markdown += '| **'+header+'** '
        } else {
          markdown += '|   '
        }

        var optionNames = option.name.trim().split(', ')
        var url = 'https://cibuildwheel.pypa.io/en/stable/options/#'+option.id;
        var namesMarkdown = $.map(optionNames, function(n) {
          return '[`'+n+'`]('+url+') '
        }).join(' <br> ')

        markdown += '| '+namesMarkdown+' '
        markdown += '| '+option.description.trim()+' '
        markdown += '|\n'
      }
    }

    console.log('readme options markdown\n', markdown)
  });
</script>

[TOML]: https://toml.io
