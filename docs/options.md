# Options

<div class="options-toc"></div>

## Build selection

### `platform` {: #platform cmd-line env-var }

> Override the auto-detected target platform

Options: `auto` `linux` `macos` `windows` `ios` `pyodide`

Default: `auto`

`auto` will build wheels for the current platform.

- For `linux`, you need [Docker or Podman](#container-engine) running, on Linux, macOS, or Windows.
- For `macos` and `windows`, you need to be running on the respective system, with a working compiler toolchain installed - Xcode Command Line tools for macOS, and MSVC for Windows.
- For `ios` you need to be running on macOS, with Xcode and the iOS simulator installed.
- For `pyodide`, you need a Linux or macOS machine.

Check the [platforms](platforms.md) page for more information on platform requirements.

This option can also be set using the [command-line option](#command-line) `--platform`. This option is not available in the `pyproject.toml` config.

!!! tip
    You can use this option to locally debug your cibuildwheel config on Linux, instead of pushing to CI to test every change. For example:

    ```bash
    export CIBW_BUILD='cp37-*'
    export CIBW_TEST_COMMAND='pytest {project}/tests'
    cibuildwheel --platform linux .
    ```

    Linux builds are the easiest to test locally, because all the build tools are supplied in the container, and they run exactly the same locally as in CI.

    This is even more convenient if you store your cibuildwheel config in [`pyproject.toml`](configuration.md#configuration-file).

    You can also run a single identifier with `--only <identifier>`. This will
    not require `--platform` or `--arch`, and will override any build/skip
    configuration.

### `build`, `skip` {: #build-skip toml env-var }

> Choose the Python versions to build

List of builds to build and skip. Each build has an identifier like `cp38-manylinux_x86_64` or `cp37-macosx_x86_64` - you can list specific ones to build and cibuildwheel will only build those, and/or list ones to skip and cibuildwheel won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `build` and does not match `skip` will be built.

When setting the options, you can use shell-style globbing syntax, as per [fnmatch](https://docs.python.org/3/library/fnmatch.html) with the addition of curly bracket syntax `{option1,option2}`, provided by [bracex](https://pypi.org/project/bracex/). All the build identifiers supported by cibuildwheel are shown below:

<div class="build-id-table-marker"></div>
|               | macOS                                                                  | Windows                                             | Linux Intel                                                                                         | Linux Other                                                                                                                                                                                                                                                                   | iOS                                                                                               | pyodide (WASM)       |
|---------------|------------------------------------------------------------------------|-----------------------------------------------------|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|----------------------|
| Python 3.8    | cp38-macosx_x86_64<br/>cp38-macosx_universal2<br/>cp38-macosx_arm64    | cp38-win_amd64<br/>cp38-win32                       | cp38-manylinux_x86_64<br/>cp38-manylinux_i686<br/>cp38-musllinux_x86_64<br/>cp38-musllinux_i686     | cp38-manylinux_aarch64<br/>cp38-manylinux_ppc64le<br/>cp38-manylinux_s390x<br/>cp38-manylinux_armv7l<br/>cp38-manylinux_riscv64<br/>cp38-musllinux_aarch64<br/>cp38-musllinux_ppc64le<br/>cp38-musllinux_s390x<br/>cp38-musllinux_armv7l<br/>cp38-musllinux_riscv64           |                                                                                                   |                      |
| Python 3.9    | cp39-macosx_x86_64<br/>cp39-macosx_universal2<br/>cp39-macosx_arm64    | cp39-win_amd64<br/>cp39-win32<br/>cp39-win_arm64    | cp39-manylinux_x86_64<br/>cp39-manylinux_i686<br/>cp39-musllinux_x86_64<br/>cp39-musllinux_i686     | cp39-manylinux_aarch64<br/>cp39-manylinux_ppc64le<br/>cp39-manylinux_s390x<br/>cp39-manylinux_armv7l<br/>cp39-manylinux_riscv64<br/>cp39-musllinux_aarch64<br/>cp39-musllinux_ppc64le<br/>cp39-musllinux_s390x<br/>cp39-musllinux_armv7l<br/>cp39-musllinux_riscv64           |                                                                                                   |                      |
| Python 3.10   | cp310-macosx_x86_64<br/>cp310-macosx_universal2<br/>cp310-macosx_arm64 | cp310-win_amd64<br/>cp310-win32<br/>cp310-win_arm64 | cp310-manylinux_x86_64<br/>cp310-manylinux_i686<br/>cp310-musllinux_x86_64<br/>cp310-musllinux_i686 | cp310-manylinux_aarch64<br/>cp310-manylinux_ppc64le<br/>cp310-manylinux_s390x<br/>cp310-manylinux_armv7l<br/>cp310-manylinux_riscv64<br/>cp310-musllinux_aarch64<br/>cp310-musllinux_ppc64le<br/>cp310-musllinux_s390x<br/>cp310-musllinux_armv7l<br/>cp310-musllinux_riscv64 |                                                                                                   |                      |
| Python 3.11   | cp311-macosx_x86_64<br/>cp311-macosx_universal2<br/>cp311-macosx_arm64 | cp311-win_amd64<br/>cp311-win32<br/>cp311-win_arm64 | cp311-manylinux_x86_64<br/>cp311-manylinux_i686<br/>cp311-musllinux_x86_64<br/>cp311-musllinux_i686 | cp311-manylinux_aarch64<br/>cp311-manylinux_ppc64le<br/>cp311-manylinux_s390x<br/>cp311-manylinux_armv7l<br/>cp311-manylinux_riscv64<br/>cp311-musllinux_aarch64<br/>cp311-musllinux_ppc64le<br/>cp311-musllinux_s390x<br/>cp311-musllinux_armv7l<br/>cp311-musllinux_riscv64 |                                                                                                   |                      |
| Python 3.12   | cp312-macosx_x86_64<br/>cp312-macosx_universal2<br/>cp312-macosx_arm64 | cp312-win_amd64<br/>cp312-win32<br/>cp312-win_arm64 | cp312-manylinux_x86_64<br/>cp312-manylinux_i686<br/>cp312-musllinux_x86_64<br/>cp312-musllinux_i686 | cp312-manylinux_aarch64<br/>cp312-manylinux_ppc64le<br/>cp312-manylinux_s390x<br/>cp312-manylinux_armv7l<br/>cp312-manylinux_riscv64<br/>cp312-musllinux_aarch64<br/>cp312-musllinux_ppc64le<br/>cp312-musllinux_s390x<br/>cp312-musllinux_armv7l<br/>cp312-musllinux_riscv64 |                                                                                                   | cp312-pyodide_wasm32 |
| Python 3.13   | cp313-macosx_x86_64<br/>cp313-macosx_universal2<br/>cp313-macosx_arm64 | cp313-win_amd64<br/>cp313-win32<br/>cp313-win_arm64 | cp313-manylinux_x86_64<br/>cp313-manylinux_i686<br/>cp313-musllinux_x86_64<br/>cp313-musllinux_i686 | cp313-manylinux_aarch64<br/>cp313-manylinux_ppc64le<br/>cp313-manylinux_s390x<br/>cp313-manylinux_armv7l<br/>cp313-manylinux_riscv64<br/>cp313-musllinux_aarch64<br/>cp313-musllinux_ppc64le<br/>cp313-musllinux_s390x<br/>cp313-musllinux_armv7l<br/>cp313-musllinux_riscv64 | cp313-ios_arm64_iphoneos<br/>cp313-ios_arm64_iphonesimulator<br/>cp313-ios_x86_64_iphonesimulator | cp313-pyodide_wasm32 |
| Python 3.14   | cp314-macosx_x86_64<br/>cp314-macosx_universal2<br/>cp314-macosx_arm64 | cp314-win_amd64<br/>cp314-win32<br/>cp314-win_arm64 | cp314-manylinux_x86_64<br/>cp314-manylinux_i686<br/>cp314-musllinux_x86_64<br/>cp314-musllinux_i686 | cp314-manylinux_aarch64<br/>cp314-manylinux_ppc64le<br/>cp314-manylinux_s390x<br/>cp314-manylinux_armv7l<br/>cp314-manylinux_riscv64<br/>cp314-musllinux_aarch64<br/>cp314-musllinux_ppc64le<br/>cp314-musllinux_s390x<br/>cp314-musllinux_armv7l<br/>cp314-musllinux_riscv64 |                                                                                                   |                      |
| PyPy3.8 v7.3  | pp38-macosx_x86_64<br/>pp38-macosx_arm64                               | pp38-win_amd64                                      | pp38-manylinux_x86_64<br/>pp38-manylinux_i686                                                       | pp38-manylinux_aarch64                                                                                                                                                                                                                                                        |                                                                                                   |                      |
| PyPy3.9 v7.3  | pp39-macosx_x86_64<br/>pp39-macosx_arm64                               | pp39-win_amd64                                      | pp39-manylinux_x86_64<br/>pp39-manylinux_i686                                                       | pp39-manylinux_aarch64                                                                                                                                                                                                                                                        |                                                                                                   |                      |
| PyPy3.10 v7.3 | pp310-macosx_x86_64<br/>pp310-macosx_arm64                             | pp310-win_amd64                                     | pp310-manylinux_x86_64<br/>pp310-manylinux_i686                                                     | pp310-manylinux_aarch64                                                                                                                                                                                                                                                       |                                                                                                   |                      |
| PyPy3.11 v7.3 | pp311-macosx_x86_64<br/>pp311-macosx_arm64                             | pp311-win_amd64                                     | pp311-manylinux_x86_64<br/>pp311-manylinux_i686                                                     | pp311-manylinux_aarch64                                                                                                                                                                                                                                                       |                                                                                                   |                      |
| GraalPy 3.11 v24.2 | gp311_242-macosx_x86_64<br/>gp311_242-macosx_arm64                             | gp311_242-win_amd64                                     | gp311_242-manylinux_x86_64                                                                              | gp311_242-manylinux_aarch64                                                                                                                                                                                                                                                       |                                                                                                   |                      |

The list of supported and currently selected build identifiers can also be retrieved by passing the `--print-build-identifiers` flag to cibuildwheel.
The format is `python_tag-platform_tag`, with tags similar to those in [PEP 425](https://www.python.org/dev/peps/pep-0425/#details).

Windows arm64 platform support is experimental.
Linux riscv64 platform support is experimental and requires an explicit opt-in through [`enable`](#enable).

See the [cibuildwheel 2 documentation](https://cibuildwheel.pypa.io/en/2.x/) for past end-of-life versions of Python.

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Only build on CPython 3.8
    build = "cp38-*"

    # Skip building on CPython 3.8 on the Mac
    skip = "cp38-macosx_x86_64"

    # Skip building on CPython 3.8 on all platforms
    skip = "cp38-*"

    # Skip CPython 3.8 on Windows
    skip = "cp38-win*"

    # Skip CPython 3.8 on 32-bit Windows
    skip = "cp38-win32"

    # Skip CPython 3.8 and CPython 3.9
    skip = ["cp38-*", "cp39-*"]

    # Skip Python 3.8 on Linux
    skip = "cp38-manylinux*"

    # Skip 32-bit builds
    skip = ["*-win32", "*-manylinux_i686"]

    # Disable building PyPy wheels on all platforms
    skip = "pp*"
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Only build on CPython 3.8
    CIBW_BUILD: cp38-*

    # Skip building on CPython 3.8 on the Mac
    CIBW_SKIP: cp38-macosx_x86_64

    # Skip building on CPython 3.8 on all platforms
    CIBW_SKIP: cp38-*

    # Skip CPython 3.8 on Windows
    CIBW_SKIP: cp38-win*

    # Skip CPython 3.8 on 32-bit Windows
    CIBW_SKIP: cp38-win32

    # Skip CPython 3.8 and CPython 3.9
    CIBW_SKIP: cp38-* cp39-*

    # Skip Python 3.8 on Linux
    CIBW_SKIP: cp38-manylinux*

    # Skip 32-bit builds
    CIBW_SKIP: "*-win32 *-manylinux_i686"

    # Disable building PyPy wheels on all platforms
    CIBW_SKIP: pp*
    ```

    Separate multiple selectors with a space.



    It is generally recommended to set `CIBW_BUILD` as an environment variable, though `skip`
    tends to be useful in a config file; you can statically declare that you don't
    support a specific build, for example.

<style>
  .build-id-table-marker + .wy-table-responsive table {
    font-size: 90%;
  }
  .rst-content .build-id-table-marker + .wy-table-responsive table td,
  .rst-content .build-id-table-marker + .wy-table-responsive table th {
    padding: 4px 8px;
    white-space: nowrap;
    background-color: white;
  }
  .build-id-table-marker + .wy-table-responsive table td:not(:first-child) {
    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
    font-size: 85%;
  }
  .build-id-table-marker + .wy-table-responsive table td:first-child,
  .build-id-table-marker + .wy-table-responsive table th:first-child {
    font-weight: bold;
  }
  dt code {
    font-size: 100%;
    background-color: rgba(41, 128, 185, 0.1);
    padding: 0;
  }
</style>


### `archs` {: #archs cmd-line env-var toml }
> Change the architectures built on your machine by default.

A list of architectures to build.

On macOS, this option can be used to [cross-compile](platforms.md#macos-architectures) between `x86_64`, `universal2` and `arm64`.

On Linux, this option can be used to build [non-native architectures under emulation](faq.md#emulation).

On Windows, this option can be used to [compile for `ARM64` from an Intel machine](platforms.md#windows-arm64), provided the cross-compiling tools are installed.

Options:

- Linux: `x86_64` `i686` `aarch64` `ppc64le` `s390x` `armv7l` `riscv64`
- macOS: `x86_64` `arm64` `universal2`
- Windows: `AMD64` `x86` `ARM64`
- Pyodide: `wasm32`
- iOS: `arm64_iphoneos` `arm64_iphonesimulator` `x86_64_iphonesimulator`
- `auto`: The default archs for your machine - see the table below.
    - `auto64`: Just the 64-bit auto archs
    - `auto32`: Just the 32-bit auto archs
- `native`: the native arch of the build machine - Matches [`platform.machine()`](https://docs.python.org/3/library/platform.html#platform.machine).
- `all` : expands to all the architectures supported on this OS. You may want
  to use [`build`](#build-skip) with this option to target specific
  architectures via build selectors.

Linux riscv64 platform support is experimental and requires an explicit opt-in through [`enable`](#enable).

Default: `auto`

| Runner | `native` | `auto` | `auto64` | `auto32` |
|---|---|---|---|---|
| Linux / Intel | `x86_64` | `x86_64` `i686` | `x86_64` | `i686` |
| Windows / Intel | `AMD64` | `AMD64` `x86` | `AMD64` | `x86` |
| Windows / ARM64 | `ARM64` | `ARM64` | `ARM64` | |
| macOS / Intel | `x86_64` | `x86_64` | `x86_64` |  |
| macOS / Apple Silicon | `arm64` | `arm64` | `arm64` |  |
| iOS on macOS / Intel | `x86_64_iphonesimulator` | `x86_64_iphonesimulator` | `x86_64_iphonesimulator` |  |
| iOS on macOS / Apple Silicon | `arm64_iphonesimulator` | `arm64_iphoneos` `arm64_iphonesimulator` | `arm64_iphoneos` `arm64_iphonesimulator` |

If not listed above, `auto` is the same as `native`.

[setup-qemu-action]: https://github.com/docker/setup-qemu-action
[binfmt]: https://hub.docker.com/r/tonistiigi/binfmt

Platform-specific environment variables are also available:<br/>
 `CIBW_ARCHS_MACOS` | `CIBW_ARCHS_WINDOWS` | `CIBW_ARCHS_LINUX` | `CIBW_ARCHS_IOS`

This option can also be set using the [command-line option](#command-line)
`--archs`. This option cannot be set in an `overrides` section in `pyproject.toml`.

#### Examples

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



    It is generally recommended to use the environment variable or
    command-line option for Linux, as selecting archs often depends
    on your specific runner having qemu installed.


###  `project-requires-python` {: #requires-python env-var}
> Manually set the Python compatibility of your project

By default, cibuildwheel reads your package's Python compatibility from
`pyproject.toml` following the [project metadata specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/)
or from `setup.cfg`; finally it will try to inspect the AST of `setup.py` for a
simple keyword assignment in a top level function call. If you need to override
this behaviour for some reason, you can use this option.

When setting this option, the syntax is the same as `project.requires-python`,
using 'version specifiers' like `>=3.8`, according to
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
        requires-python = ">=3.8"
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
    CIBW_PROJECT_REQUIRES_PYTHON: ">=3.8"
    ```

### `enable` {: #enable toml env-var}
> Enable building with extra categories of selectors present.

This option lets you opt-in to non-default builds, like pre-releases and
free-threaded Python. These are not included by default to give a nice default
for new users, but can be added to the selectors available here. The allowed
values are:


- `cpython-prerelease`: Enables beta versions of Pythons if any are available
  (May-July, approximately).
- `cpython-freethreading`: [PEP 703](https://www.python.org/dev/peps/pep-0703)
  introduced variants of CPython that can be built without the Global
  Interpreter Lock (GIL).  Those variants are also known as free-threaded /
  no-gil. This will enable building these wheels while they are experimental.
  The build identifiers for those variants have a `t` suffix in their
  `python_tag` (e.g. `cp313t-manylinux_x86_64`).
- `pypy`: Enable PyPy.
- `pypy-eol`: Enable PyPy versions that have passed end of life (if still available).
- `cpython-experimental-riscv64`: Enable experimental riscv64 builds. Those builds
  are disabled by default as they can't be uploaded to PyPI and a PEP will most likely
  be required before this can happen.
- `graalpy`: Enable GraalPy.
- `pyodide-prerelease`: Pyodide versions that haven't released yet, if one is
  available. Safe if you are shipping a site with an early build, not for
  general distribution.
- `all`: Enable all of the above.

!!! caution
    `cpython-prerelease` is provided for testing purposes only. It is not
    recommended to distribute wheels built with beta releases, such as
    uploading to PyPI.  Please _do not_ upload these wheels to PyPI (except for
    pre-releases), as they are not guaranteed to work with the final Python
    release.  Once Python is ABI stable and enters the release candidate phase,
    that version of Python will become available without this flag.

!!! note
    Free threading is experimental: [What’s New In Python 3.13](https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython)

Default: empty.

This option doesn't support overrides or platform specific variants; it is
intended as a way to acknowledge that a project is aware that these extra
selectors exist.  If you need to enable/disable it per platform or python
version, set this option to `true` and use
[`build`](#build-skip)/[`skip`](#build-skip) options to filter the
builds.

Unlike all other cibuildwheel options, the environment variable setting will
only add to the TOML config; you can't remove an enable by setting an empty or
partial list in environment variables; use `CIBW_SKIP` instead. This way, if
you apply `cpython-prerelease` during the beta period using `CIBW_ENABLE`
without disabling your other enables.


#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Enable free-threaded support
    enable = ["cpython-freethreading"]

    # Skip building free-threaded compatible wheels on Windows
    enable = ["cpython-freethreading"]
    skip = "*t-win*"

    # Include all PyPy versions
    enable = ["pypy", "pypy-eol"]
    ```


!!! tab examples "Environment variables"

    ```yaml
    # Include latest Python beta
    CIBW_ENABLE: cpython-prerelease

    # Include free-threaded support
    CIBW_ENABLE: cpython-freethreading

    # Include both
    CIBW_ENABLE: cpython-prerelease cpython-freethreading

    # Skip building free-threaded compatible wheels on Windows
    CIBW_ENABLE: cpython-freethreading
    CIBW_SKIP: *t-win*

    # Include all PyPy versions
    CIBW_ENABLE = pypy pypy-eol
    ```



### `allow-empty` {: #allow-empty cmd-line env-var}
> Suppress the error code if no wheels match the specified build identifiers

When none of the specified build identifiers match any available versions,
cibuildwheel will typically return error code 3, indicating that there are
no wheels to build. Enabling this option will suppress this error, allowing
the build process to complete without signaling an error.

Default: Off (0). Error code 3 is returned when no builds are selected.

This option can also be set using the [command-line option](#command-line)
`--allow-empty`. This option is not available in the `pyproject.toml` config.

#### Examples

!!! tab examples "Environment variables"

    ```yaml
    # Prevent an error code if the build does not match any wheels
    CIBW_ALLOW_EMPTY: True
    ```

## Build customization

### `build-frontend` {: #build-frontend toml env-var}
> Set the tool to use to build, either "build" (default), "build\[uv\]", or "pip"

Options:

- `build[;args: ...]`
- `build[uv][;args: ...]`
- `pip[;args: ...]`

Default: `build`

Choose which build frontend to use.

You can use "build\[uv\]", which will use an external [uv][] everywhere
possible, both through `--installer=uv` passed to build, as well as when making
all build and test environments. This will generally speed up cibuildwheel.
Make sure you have an external uv on Windows and macOS, either by
pre-installing it, or installing cibuildwheel with the uv extra,
`cibuildwheel[uv]`. You cannot use uv currently on Windows for ARM, for
musllinux on s390x, or for iOS, as binaries are not provided by uv. Legacy dependencies like
setuptools on Python < 3.12 and pip are not installed if using uv.

Pyodide ignores this setting, as only "build" is supported.

You can specify extra arguments to pass to the build frontend using the
optional `args` option.

!!! warning
    If you are using `build[uv]` and are passing `--no-isolation` or `-n`, we
    will detect this and avoid passing `--installer=uv` to build, but still
    install all packages with uv. We do not currently detect combined short
    options, like `-xn`!

[pip]: https://pip.pypa.io/en/stable/cli/pip_wheel/
[build]: https://github.com/pypa/build/
[uv]: https://github.com/astral-sh/uv

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Switch to using pip
    build-frontend = "pip"

    # supply an extra argument to 'pip wheel'
    build-frontend = { name = "pip", args = ["--no-build-isolation"] }

    # Use uv and build
    build-frontend = "build[uv]"

    # Use uv and build with an argument
    build-frontend = { name = "build[uv]", args = ["--no-isolation"] }
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Switch to using pip
    CIBW_BUILD_FRONTEND: "pip"

    # supply an extra argument to 'pip wheel'
    CIBW_BUILD_FRONTEND: "pip; args: --no-build-isolation"

    # Use uv and build
    CIBW_BUILD_FRONTEND: "build[uv]"

    # Use uv and build with an argument
    CIBW_BUILD_FRONTEND: "build[uv]; args: --no-isolation"
    ```



### `config-settings` {: #config-settings env-var toml}
> Specify config-settings for the build backend.

Specify config settings for the build backend. Each space separated
item will be passed via `--config-setting`. In TOML, you can specify
a table of items, including arrays.

!!! tip
    Currently, "build" supports arrays for options, but "pip" only supports
    single values.

Platform-specific environment variables also available:<br/>
`CIBW_CONFIG_SETTINGS_MACOS` | `CIBW_CONFIG_SETTINGS_WINDOWS` | `CIBW_CONFIG_SETTINGS_LINUX` | `CIBW_CONFIG_SETTINGS_IOS` | `CIBW_CONFIG_SETTINGS_PYODIDE`


#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.config-settings]
    --build-option = "--use-mypyc"
    ```

!!! tab examples "Environment variables"

    ```yaml
    CIBW_CONFIG_SETTINGS: "--build-option=--use-mypyc"
    ```




### `environment` {: #environment env-var toml}
> Set environment variables

A list of environment variables to set during the build and test phases. Bash syntax should be used, even on Windows.

You must use this variable to pass variables to Linux builds, since they execute in a container. It also works for the other platforms.

You can use `$PATH` syntax to insert other variables, or the `$(pwd)` syntax to insert the output of other shell commands.

To specify more than one environment variable, separate the assignments by spaces.

Platform-specific environment variables are also available:<br/>
`CIBW_ENVIRONMENT_MACOS` | `CIBW_ENVIRONMENT_WINDOWS` | `CIBW_ENVIRONMENT_LINUX` | `CIBW_ENVIRONMENT_IOS` | `CIBW_ENVIRONMENT_PYODIDE`

#### Examples

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

    In configuration files, you can use a [TOML][] table instead of a raw string as shown above.

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

!!! note
    cibuildwheel always defines the environment variable `CIBUILDWHEEL=1`. This can be useful for [building wheels with optional extensions](faq.md#optional-extensions).

!!! note
    To do its work, cibuildwheel sets the variables `VIRTUALENV_PIP`, `DIST_EXTRA_CONFIG`, `SETUPTOOLS_EXT_SUFFIX`, `PIP_DISABLE_PIP_VERSION_CHECK`, `PIP_ROOT_USER_ACTION`, and it extends the variables `PATH` and `PIP_CONSTRAINT`. Your assignments to these options might be replaced or extended.

### `environment-pass` {: #environment-pass env-var="CIBW_ENVIRONMENT_PASS_LINUX" toml}
> Set environment variables on the host to pass-through to the container.

A list of environment variables to pass into the linux container during each build and test. It has no effect on the other platforms, which can already access all environment variables directly.

To specify more than one environment variable, separate the variable names by spaces.

!!! note
    cibuildwheel automatically passes the environment variable [`SOURCE_DATE_EPOCH`](https://reproducible-builds.org/docs/source-date-epoch/) if defined.

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.linux]

    # Export a variable
    environment-pass = ["CFLAGS"]

    # Set two flags variables
    environment-pass = ["BUILD_TIME", "SAMPLE_TEXT"]
    ```

    In configuration files, you can use a [TOML][] list instead of a raw string as shown above.

!!! tab examples "Environment variables"

    ```yaml
    # Export a variable
    CIBW_ENVIRONMENT_PASS_LINUX: CFLAGS

    # Set two flags variables
    CIBW_ENVIRONMENT_PASS_LINUX: BUILD_TIME SAMPLE_TEXT
    ```

    Separate multiple values with a space.

### `before-all` {: #before-all env-var toml}
> Execute a shell command on the build system before any wheels are built.

Shell command that runs before any builds are run, to build or install parts that do not depend on the specific version of Python.

This option is very useful for the Linux build, where builds take place in isolated containers managed by cibuildwheel. This command will run inside the container before the wheel builds start. Note, if you're building both `x86_64` and `i686` wheels (the default), your build uses two different container images. In that case, this command will execute twice - once per build container.

The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

On Windows and macOS, the version of Python available inside `before-all` is whatever is available on the host machine. On Linux, a modern Python version is available on PATH.

This option has special behavior in the overrides section in `pyproject.toml`.
On linux, overriding it triggers a new container launch. It cannot be overridden
on macOS and Windows.

Platform-specific environment variables also available:<br/>
`CIBW_BEFORE_ALL_MACOS` | `CIBW_BEFORE_ALL_WINDOWS` | `CIBW_BEFORE_ALL_LINUX` | `CIBW_BEFORE_ALL_IOS` | `CIBW_BEFORE_ALL_PYODIDE`

!!! note

    This command is executed in a different Python environment from the builds themselves. So you can't `pip install` a Python dependency in `before-all` and use it in the build. Instead, look at [`before-build`](#before-build), or, if your project uses pyproject.toml, the [build-system.requires](https://peps.python.org/pep-0518/#build-system-table) field.

#### Examples

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


Note that `manylinux_2_31` builds occur inside a Debian derivative docker
container, where `manylinux2014` builds occur inside a CentOS one. So for
`manylinux_2_31` the `before-all` command must use `apt-get -y`
instead.

### `before-build` {: #before-build env-var toml}
> Execute a shell command preparing each wheel's build

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), instead of using this command, we recommend adding requirements to a `pyproject.toml` file's `build-system.requires` array instead. This is reproducible, and users who do not get your wheels (such as Alpine or ClearLinux users) will still benefit.

The active Python binary can be accessed using `python`, and pip with `pip`; cibuildwheel makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX` | `CIBW_BEFORE_BUILD_IOS` | `CIBW_BEFORE_BUILD_PYODIDE`

#### Examples

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

    In configuration files, you can use a array, and the items will be joined
    with `&&`. In TOML, using a single-quote string will avoid escapes - useful for
    Windows paths.

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


!!! note
    If you need Python dependencies installed for the build, we recommend using
    `pyproject.toml`'s `build-system.requires` instead. This is an example
    `pyproject.toml` file:

        [build-system]
        requires = [
            "setuptools>=42",
            "Cython",
            "numpy",
        ]

        build-backend = "setuptools.build_meta"

    This [PEP 517][]/[PEP 518][] style build allows you to completely control
    the build environment in cibuildwheel, [PyPA-build][], and pip, doesn't
    force downstream users to install anything they don't need, and lets you do
    more complex pinning.

    [PyPA-build]: https://pypa-build.readthedocs.io/en/latest/
    [PEP 517]: https://www.python.org/dev/peps/pep-0517/
    [PEP 518]: https://www.python.org/dev/peps/pep-0517/

### `xbuild-tools` {: #xbuild-tools env-var toml}
> Binaries on the path that should be included in an isolated cross-build environment.

When building in a cross-platform environment, it is sometimes necessary to isolate the ``PATH`` so that binaries from the build machine don't accidentally get linked into the cross-platform binary. However, this isolation process will also hide tools that might be required to build your wheel.

If there are binaries present on the `PATH` when you invoke cibuildwheel, and those binaries are required to build your wheels, those binaries can be explicitly included in the isolated cross-build environment using `xbuild-tools`. The binaries listed in this setting will be linked into an isolated location, and that isolated location will be put on the `PATH` of the isolated environment. You do not need to provide the full path to the binary - only the executable name that would be found by the shell.

If you declare a tool as a cross-build tool, and that tool cannot be found in the runtime environment, an error will be raised.

If you do not define `xbuild-tools`, and you build for a platform that uses a cross-platform environment, a warning will be raised. If your project does not require any cross-build tools, you can set `xbuild-tools` to an empty list to silence this warning.

*Any* tool used by the build process must be included in the `xbuild-tools` list, not just tools that cibuildwheel will invoke directly. For example, if your build invokes `cmake`, and the `cmake` script invokes `magick` to perform some image transformations, both `cmake` and `magick` must be included in your safe tools list.

Platform-specific environment variables are also available on platforms that use cross-platform environment isolation:<br/>
 `CIBW_XBUILD_TOOLS_IOS`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Allow access to the cmake and rustc binaries in the isolated cross-build environment.
    xbuild-tools = ["cmake", "rustc"]

    # No cross-build tools are required
    xbuild-tools = []
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Allow access to the cmake and rustc binaries in the isolated cross-build environment.
    CIBW_XBUILD_TOOLS: cmake rustc

    # No cross-build tools are required
    CIBW_XBUILD_TOOLS:
    ```


### `repair-wheel-command` {: #repair-wheel-command env-var toml}
> Execute a shell command to repair each built wheel

Default:

- on Linux: `'auditwheel repair -w {dest_dir} {wheel}'`
- on macOS: `'delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}'`
- on Windows: `''`
- on iOS: `''`
- on Pyodide: `''`

A shell command to repair a built wheel by copying external library dependencies into the wheel tree and relinking them.
The command is run on each built wheel (except for pure Python ones) before testing it.

The following placeholders must be used inside the command and will be replaced by cibuildwheel:

- `{wheel}` for the absolute path to the built wheel
- `{dest_dir}` for the absolute path of the directory where to create the repaired wheel
- `{delocate_archs}` (macOS only) comma-separated list of architectures in the wheel.

The command is run in a shell, so you can run multiple commands like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
`CIBW_REPAIR_WHEEL_COMMAND_MACOS` | `CIBW_REPAIR_WHEEL_COMMAND_WINDOWS` | `CIBW_REPAIR_WHEEL_COMMAND_LINUX` | `CIBW_REPAIR_WHEEL_COMMAND_IOS` | `CIBW_REPAIR_WHEEL_COMMAND_PYODIDE`

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
    repair-wheel-command = [
      "copy {wheel} {dest_dir}",
      "pipx run abi3audit --strict --report {wheel}",
    ]
    ```

    In configuration files, you can use an inline array, and the items will be joined with `&&`.


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
      copy {wheel} {dest_dir} &&
      pipx run abi3audit --strict --report {wheel}
    ```


<div class="link-target" id="manylinux-image"></div>

### `manylinux-*-image`, `musllinux-*-image` {: #linux-image env-var toml}

> Specify manylinux / musllinux container images

The available options are:

| Option                         | Default                                                         |
|--------------------------------|-----------------------------------------------------------------|
| `manylinux_x86_64-image`       | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_x86_64)  |
| `manylinux-i686-image`         | [`manylinux2014`](https://quay.io/pypa/manylinux2014_i686)      |
| `manylinux-pypy_x86_64-image`  | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_x86_64)  |
| `manylinux-aarch64-image`      | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_aarch64) |
| `manylinux-ppc64le-image`      | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_ppc64le) |
| `manylinux-s390x-image`        | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_s390x)   |
| `manylinux-armv7l-image`       | [`manylinux_2_31`](https://quay.io/pypa/manylinux_2_31_armv7l)  |
| `manylinux-riscv64-image`      | No default                                                      |
| `manylinux-pypy_aarch64-image` | [`manylinux_2_28`](https://quay.io/pypa/manylinux_2_28_aarch64) |
| `manylinux-pypy_i686-image`    | [`manylinux2014`](https://quay.io/pypa/manylinux2014_i686)      |
| `musllinux_x86_64-image`       | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_x86_64)    |
| `musllinux-i686-image`         | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_i686)      |
| `musllinux-aarch64-image`      | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_aarch64)   |
| `musllinux-ppc64le-image`      | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_ppc64le)   |
| `musllinux-s390x-image`        | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_s390x)     |
| `musllinux-armv7l-image`       | [`musllinux_1_2`](https://quay.io/pypa/musllinux_1_2_armv7l)    |
| `musllinux-riscv64-image`      | No default                                                      |

Set the Docker image to be used for building [manylinux / musllinux](https://github.com/pypa/manylinux) wheels.

For `manylinux-*-image`, except `manylinux-armv7l-image`, the value of this option can either be set to `manylinux2014`, `manylinux_2_28` or `manylinux_2_34` to use a pinned version of the [official manylinux images](https://github.com/pypa/manylinux). Alternatively, set these options to any other valid Docker image name.
`manylinux_2_28` and `manylinux_2_34` are not supported for `i686` architecture.

For `manylinux-armv7l-image`, the value of this option can either be set to `manylinux_2_31` or a custom image. Support is experimental for now. The `manylinux_2_31` value is only available for `armv7`.

For `musllinux-*-image`, the value of this option can either be set to `musllinux_1_2` or a custom image.

If this option is blank, it will fall though to the next available definition (environment variable -> pyproject.toml -> default).

If setting a custom image, you'll need to make sure it can be used in the same way as the default images: all necessary Python and pip versions need to be present in `/opt/python/`, and the auditwheel tool needs to be present for cibuildwheel to work. Apart from that, the architecture and relevant shared system libraries need to be compatible to the relevant standard to produce valid manylinux2014/manylinux_2_28/manylinux_2_34/musllinux_1_2 wheels (see [pypa/manylinux on GitHub](https://github.com/pypa/manylinux), [PEP 599](https://www.python.org/dev/peps/pep-0599/), [PEP 600](https://www.python.org/dev/peps/pep-0600/) and [PEP 656](https://www.python.org/dev/peps/pep-0656/) for more details).

Auditwheel detects the version of the manylinux / musllinux standard in the image through the `AUDITWHEEL_PLAT` environment variable, as cibuildwheel has no way of detecting the correct `--plat` command line argument to pass to auditwheel for a custom image. If a custom image does not correctly set this `AUDITWHEEL_PLAT` environment variable, the `CIBW_ENVIRONMENT` option can be used to do so (e.g., `CIBW_ENVIRONMENT='AUDITWHEEL_PLAT="manylinux2014_$(uname -m)"'`).

!!! warning
    On x86_64, `manylinux_2_34` is using [x86-64-v2](https://en.wikipedia.org/wiki/X86-64#Microarchitecture_levels) target architecture.

    While manylinux worked around that when building extensions from sources by intercepting compiler calls
    to target x86_64 instead, every library installed with dnf will most likely target the more
    recent x86-64-v2 which, if grafted into a wheel, will fail to run on older hardware.

    The workaround does not work for executables as they are always being linked with x86-64-v2 object files.

    There's no PEP to handle micro-architecture variants yet when it comes to packaging or
    installing wheels. Auditwheel doesn't detect this either.

    Please check the tracking issue in [pypa/manylinux](https://github.com/pypa/manylinux/issues/1725)


#### Examples


!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Build using the manylinux2014 image
    manylinux-x86_64-image = "manylinux2014"
    manylinux-i686-image = "manylinux2014"
    manylinux-pypy_x86_64-image = "manylinux2014"
    manylinux-pypy_i686-image = "manylinux2014"

    # Build using the latest manylinux2010 release
    manylinux-x86_64-image = "quay.io/pypa/manylinux2010_x86_64:latest"
    manylinux-i686-image = "quay.io/pypa/manylinux2010_i686:latest"
    manylinux-pypy_x86_64-image = "quay.io/pypa/manylinux2010_x86_64:latest"
    manylinux-pypy_i686-image = "quay.io/pypa/manylinux2010_i686:latest"

    # Build using a different image from the docker registry
    manylinux-x86_64-image = "dockcross/manylinux-x64"
    manylinux-i686-image = "dockcross/manylinux-x86"

    # Build musllinux wheels using the musllinux_1_1 image
    musllinux-x86_64-image = "quay.io/pypa/musllinux_1_1_x86_64:latest"
    musllinux-i686-image = "quay.io/pypa/musllinux_1_1_i686:latest"
    ```

    Like any other option, these can be placed in `[tool.cibuildwheel.linux]`
    if you prefer; they have no effect on `macos` and `windows`.

!!! tab examples "Environment variables"

    ```yaml
    # Build using the manylinux2014 image
    CIBW_MANYLINUX_X86_64_IMAGE: manylinux2014
    CIBW_MANYLINUX_I686_IMAGE: manylinux2014
    CIBW_MANYLINUX_PYPY_X86_64_IMAGE: manylinux2014
    CIBW_MANYLINUX_PYPY_I686_IMAGE: manylinux2014

    # Build using the latest manylinux2010 release
    CIBW_MANYLINUX_X86_64_IMAGE: quay.io/pypa/manylinux2010_x86_64:latest
    CIBW_MANYLINUX_I686_IMAGE: quay.io/pypa/manylinux2010_i686:latest
    CIBW_MANYLINUX_PYPY_X86_64_IMAGE: quay.io/pypa/manylinux2010_x86_64:latest
    CIBW_MANYLINUX_PYPY_I686_IMAGE: quay.io/pypa/manylinux2010_i686:latest

    # Build using a different image from the docker registry
    CIBW_MANYLINUX_X86_64_IMAGE: dockcross/manylinux-x64
    CIBW_MANYLINUX_I686_IMAGE: dockcross/manylinux-x86

    # Build musllinux wheels using the musllinux_1_1 image
    CIBW_MUSLLINUX_X86_64_IMAGE: quay.io/pypa/musllinux_1_1_x86_64:latest
    CIBW_MUSLLINUX_I686_IMAGE: quay.io/pypa/musllinux_1_1_i686:latest
    ```


### `container-engine` {: #container-engine env-var toml}
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

!!! tab examples "Environment variables"

    ```yaml
    # use podman instead of docker
    CIBW_CONTAINER_ENGINE: podman

    # pass command line options to 'docker create'
    CIBW_CONTAINER_ENGINE: "docker; create_args: --gpus all"

    # disable the /host mount
    CIBW_CONTAINER_ENGINE: "docker; disable_host_mount: true"
    ```



### `dependency-versions` {: #dependency-versions env-var toml}

> Control the versions of the tools cibuildwheel uses

Options: `pinned` `latest` `packages: SPECIFIER...` `<your constraints file>`

Default: `pinned`

If `dependency-versions` is `pinned`, cibuildwheel uses versions of tools
like `pip`, `setuptools`, `virtualenv` that were pinned with that release of
cibuildwheel. This represents a known-good set of dependencies, and is
recommended for build repeatability.

If set to `latest`, cibuildwheel will use the latest of these packages that
are available on PyPI. This might be preferable if these packages have bug
fixes that can't wait for a new cibuildwheel release.

To control the versions of dependencies yourself, you can supply a [pip
constraints](https://pip.pypa.io/en/stable/user_guide/#constraints-files) file
here and it will be used instead. Alternatively, you can list constraint
specifiers inline with the `packages: SPECIFIER...` syntax.

!!! note
    If you need different dependencies for each python version, provide them
    in the same folder with a `-pythonXY` suffix. e.g. if your
    `dependency-versions="./constraints.txt"`, cibuildwheel will use
    `./constraints-python38.txt` on Python 3.8, or fallback to
    `./constraints.txt` if that's not found.

Platform-specific environment variables are also available:<br/>
`CIBW_DEPENDENCY_VERSIONS_MACOS` | `CIBW_DEPENDENCY_VERSIONS_WINDOWS` | `CIBW_DEPENDENCY_VERSIONS_IOS` | `CIBW_DEPENDENCY_VERSIONS_PYODIDE`

!!! note
    This option does not affect the tools used on the Linux build - those versions
    are bundled with the manylinux/musllinux image that cibuildwheel uses. To change
    dependency versions on Linux, use the [`manylinux-*` / `musllinux-*`](#linux-image)
    options.

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Use tools versions that are bundled with cibuildwheel (this is the default)
    dependency-versions = "pinned"

    # Use the latest versions available on PyPI
    dependency-versions = "latest"

    # Use your own pip constraints file
    dependency-versions = { file = "./constraints.txt" }

    # Specify requirements inline
    dependency-versions = { packages = ["auditwheel==6.2.0"] }

    [tool.cibuildwheel.pyodide]
    # Choose a specific pyodide-build version
    dependency-versions = { packages = ["pyodide-build==0.29.1"] }
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Use tools versions that are bundled with cibuildwheel (this is the default)
    CIBW_DEPENDENCY_VERSIONS: pinned

    # Use the latest versions available on PyPI
    CIBW_DEPENDENCY_VERSIONS: latest

    # Use your own pip constraints file
    CIBW_DEPENDENCY_VERSIONS: ./constraints.txt

    # Specify requirements inline
    CIBW_DEPENDENCY_VERSIONS: "packages: auditwheel==6.2.0"

    # Choose a specific pyodide-build version
    CIBW_DEPENDENCY_VERSIONS_PYODIDE: "packages: pyodide-build==0.29.1"

    # Use shell-style quoting around spaces package specifiers
    CIBW_DEPENDENCY_VERSIONS: "packages: 'pip >=16.0.0, !=17'"
    ```



### `pyodide-version` {: #pyodide-version toml env-var }

> Specify the Pyodide version to use for `pyodide` platform builds

This option allows you to specify a specific version of Pyodide to be used when building wheels for the `pyodide` platform. If unset, cibuildwheel will use a pinned Pyodide version.

This option is particularly useful for:

- Testing against specific Pyodide alpha or older releases.
- Ensuring reproducibility by targeting a known Pyodide version.

The available Pyodide versions are determined by the version of `pyodide-build` being used. You can list the compatible versions using the command `pyodide xbuildenv search --all` as described in the [Pyodide platform documentation](platforms.md#pyodide-choosing-a-version).

!!! tip
    You can set the version of `pyodide-build` using the [`dependency-versions`](#dependency-versions) option.

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.pyodide]
    # Build Pyodide wheels using Pyodide version 0.27.6
    pyodide-version = "0.27.6"

    [tool.cibuildwheel.pyodide]
    # Build Pyodide wheels using a specific alpha release
    pyodide-version = "0.28.0a2"
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Build Pyodide wheels using Pyodide version 0.27.6
    CIBW_PYODIDE_VERSION: 0.27.6

    # Build Pyodide wheels using a specific alpha release
    CIBW_PYODIDE_VERSION: 0.28.0a2
    ```


## Testing

### `test-command` {: #test-command env-var toml}
> The command to test each built wheel

Shell command to run tests after the build. The wheel will be installed
automatically and available for import from the tests. If this variable is not
set, your wheel will not be installed after building.

To ensure the wheel is imported by your tests (instead of your source copy),
**Tests are executed from a temporary directory**, outside of your source
tree. To access your test code, you have a couple of options:

- You can use the [`test-sources`](#test-sources) setting to copy specific
  files from your source tree into the temporary directory. When using
  test-sources, use relative paths in your test command, as if they were
  relative to the project root.

- You can use the `{package}` or `{project}` placeholders in your
  `test-command` to refer to the package being built or the project root,
  respectively.

    - `{package}` is the path to the package being built - the `package_dir`
      argument supplied to cibuildwheel on the command line.
    - `{project}` is an absolute path to the project root - the working
      directory where cibuildwheel was called.

On all platforms other than iOS, the command is run in a shell, so you can write things like `cmd1 && cmd2`.

On iOS, the value of the `test-command` setting must follow the format `python
-m MODULE [ARGS...]` - where MODULE is a Python module name, followed by
arguments that will be assigned to `sys.argv`. Other commands cannot be used.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX` | `CIBW_TEST_COMMAND_IOS` | `CIBW_TEST_COMMAND_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Run the package tests using `pytest`
    test-command = "pytest {project}/tests"

    # Trigger an install of the package, but run nothing of note
    test-command = "echo Wheel installed"

    # Multiline example
    test-command = [
      "pytest {project}/tests",
      "python {project}/test.py",
    ]

    # run tests on ios - when test-sources is set, use relative paths, not {project} or {package}
    [tool.cibuildwheel.ios]
    test-sources = ["tests"]
    test-command = "python -m pytest ./tests"
    ```

    In configuration files, you can use an array, and the items will be joined with `&&`.

!!! tab examples "Environment variables"

    ```yaml
    # Run the package tests using `pytest`
    CIBW_TEST_COMMAND: pytest {project}/tests

    # Trigger an install of the package, but run nothing of note
    CIBW_TEST_COMMAND: "echo Wheel installed"

    # Multi-line example - join with && on all platforms
    CIBW_TEST_COMMAND: >
      pytest {project}/tests &&
      python {project}/test.py

    # run tests on ios - when test-sources is set, use relative paths, not {project} or {package}
    CIBW_TEST_SOURCES_IOS: tests
    CIBW_TEST_COMMAND_IOS: python -m pytest ./tests
    ```

### `before-test` {: #before-test env-var toml}
> Execute a shell command before testing each wheel

A shell command to run in **each** test virtual environment, before your wheel is installed and tested. This is useful if you need to install a non-pip package, invoke pip with different environment variables,
or perform a multi-step pip installation (e.g. installing scikit-build or Cython before installing test package).

The active Python binary can be accessed using `python`, and pip with `pip`; cibuildwheel makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by cibuildwheel.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific environment variables are also available:<br/>
 `CIBW_BEFORE_TEST_MACOS` | `CIBW_BEFORE_TEST_WINDOWS` | `CIBW_BEFORE_TEST_LINUX` | `CIBW_BEFORE_TEST_IOS` | `CIBW_BEFORE_TEST_PYODIDE`

#### Examples

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


### `test-sources` {: #test-sources env-var toml}
> Files and folders from the source tree that are copied into an isolated tree before running the tests

A space-separated list of files and folders, relative to the root of the
project, required for running the tests. If specified, these files and folders
will be copied into a temporary folder, and that temporary folder will be used
as the working directory for running the test suite.

The use of `test-sources` is *required* for iOS builds. This is because the
simulator does not have access to the project directory, as it is not stored on
the simulator device. On iOS, the files will be copied into the test application,
rather than a temporary folder.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_SOURCES_MACOS` | `CIBW_TEST_SOURCES_WINDOWS` | `CIBW_TEST_SOURCES_LINUX` | `CIBW_TEST_SOURCES_IOS` | `CIBW_TEST_SOURCES_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    # Copy the "tests" folder, plus "data/test-image.png" from the source folder to the test folder.
    [tool.cibuildwheel]
    test-sources = ["tests", "data/test-image.png"]
    ```

    In configuration files, you can use an array, and the items will be joined with a space.

!!! tab examples "Environment variables"

    ```yaml
    # Copy the "tests" folder, plus "data/test-image.png" from the source folder to the test folder.
    CIBW_TEST_SOURCES: tests data/test-image.png
    ```


### `test-requires` {: #test-requires env-var toml}
> Install Python dependencies before running the tests

Space-separated list of dependencies required for running the tests.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX` | `CIBW_TEST_REQUIRES_IOS` | `CIBW_TEST_REQUIRES_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    # Install pytest before running test-command
    [tool.cibuildwheel]
    test-requires = "pytest"

    # Install specific versions of test dependencies
    [tool.cibuildwheel]
    test-requires = ["pytest==8.2.2", "packaging==24.1"]
    ```

    In configuration files, you can use an array, and the items will be joined with a space.

!!! tab examples "Environment variables"

    ```yaml
    # Install pytest before running CIBW_TEST_COMMAND
    CIBW_TEST_REQUIRES: pytest

    # Install specific versions of test dependencies
    CIBW_TEST_REQUIRES: pytest==8.2.2 packaging==24.1
    ```



### `test-extras` {: #test-extras env-var toml}
> Install your wheel for testing using `extras_require`

List of
[extras_require](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#declaring-required-dependency)
options that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`test-requires` if they are already defined in `pyproject.toml`,
`setup.cfg` or `setup.py`.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_EXTRAS_MACOS` | `CIBW_TEST_EXTRAS_WINDOWS` | `CIBW_TEST_EXTRAS_LINUX` | `CIBW_TEST_EXTRAS_IOS` | `CIBW_TEST_EXTRAS_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`
    test-extras = ["test", "qt"]
    ```

    In configuration files, you can use an inline array, and the items will be joined with a comma.

!!! tab examples "Environment variables"

    ```yaml
    # Will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`
    CIBW_TEST_EXTRAS: "test,qt"
    ```

    Separate multiple items with a comma.



### `test-groups` {: #test-groups env-var toml}
> Specify test dependencies from your project's `dependency-groups`

List of
[dependency-groups](https://peps.python.org/pep-0735)
that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`test-requires` if they are already defined in `pyproject.toml`.

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_GROUPS_MACOS` | `CIBW_TEST_GROUPS_WINDOWS` | `CIBW_TEST_GROUPS_LINUX` | `CIBW_TEST_GROUPS_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Will cause the wheel to be installed with these groups of dependencies
    test-groups = ["test", "qt"]
    ```

    In configuration files, you can use an inline array, and the items will be joined with a space.


!!! tab examples "Environment variables"

    ```yaml
    # Will cause the wheel to be installed with these groups of dependencies
    CIBW_TEST_GROUPS: "test qt"
    ```

    Separate multiple items with a space.

### `test-skip` {: #test-skip env-var toml}
> Skip running tests on some builds

This will skip testing on any identifiers that match the given skip patterns (see [`skip`](#build-skip)). This can be used to mask out tests for wheels that have missing dependencies upstream that are slow or hard to build, or to skip slow tests on emulated architectures.

With macOS `universal2` wheels, you can also skip the individual archs inside the wheel using an `:arch` suffix. For example, `cp39-macosx_universal2:x86_64` or `cp39-macosx_universal2:arm64`.

This option is not supported in the overrides section in `pyproject.toml`.

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Will avoid testing on emulated architectures
    test-skip = "*-*linux_{aarch64,ppc64le,s390x,armv7l}"

    # Skip trying to test arm64 builds on Intel Macs
    test-skip = "*-macosx_arm64 *-macosx_universal2:arm64"
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Will avoid testing on emulated architectures
    CIBW_TEST_SKIP: "*-*linux_{aarch64,ppc64le,s390x,armv7l}"

    # Skip trying to test arm64 builds on Intel Macs
    CIBW_TEST_SKIP: "*-macosx_arm64 *-macosx_universal2:arm64"
    ```


### `test-environment` {: #test-environment toml env-var }

> Set environment variables for the test environment

A space-separated list of environment variables to set in the test environment.

The syntax is the same as for [`environment`](#environment).

Platform-specific environment variables are also available:<br/>
`CIBW_TEST_ENVIRONMENT_MACOS` | `CIBW_TEST_ENVIRONMENT_WINDOWS` | `CIBW_TEST_ENVIRONMENT_LINUX` | `CIBW_TEST_ENVIRONMENT_IOS` | `CIBW_TEST_ENVIRONMENT_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Set the environment variable MY_ENV_VAR to "my_value" in the test environment
    test-environment = { MY_ENV_VAR="my_value" }

    # Set PYTHONSAFEPATH in the test environment
    test-environment = { PYTHONSAFEPATH="1" }
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Set the environment variable MY_ENV_VAR to "my_value" in the test environment
    CIBW_TEST_ENVIRONMENT: MY_ENV_VAR=my_value

    # Set PYTHONSAFEPATH in the test environment
    CIBW_TEST_ENVIRONMENT: PYTHONSAFEPATH=1
    ```


## Debugging

### `debug-keep-container` {: #debug-keep-container env-var}
> Keep the container after running for debugging.

Enable this flag to keep the container around for inspection after a build. This
option is provided for debugging purposes only.

Default: Off (0).

!!! caution
    This option can only be set as environment variable on the host machine

#### Examples

```shell
export CIBW_DEBUG_KEEP_CONTAINER=TRUE
```

### `debug-traceback` {: #debug-traceback cmd-line env-var}
> Print full traceback when errors occur.

Print a full traceback for the cibuildwheel process when errors occur. This
option is provided for debugging cibuildwheel.

This option can also be set using the [command-line option](#command-line) `--debug-traceback`.

#### Examples

```shell
export CIBW_DEBUG_TRACEBACK=TRUE
```

### `build-verbosity` {: #build-verbosity env-var toml}
> Increase/decrease the output of the build

This setting controls `-v`/`-q` flags to the build frontend. Since there is
no communication between the build backend and the build frontend, build
messages from the build backend will always be shown with `1`; higher levels
will not produce more logging about the build itself. Other levels only affect
the build frontend output, which is usually things like resolving and
downloading dependencies. The settings are:

|             | build | pip    | desc                             |
|-------------|-------|--------|----------------------------------|
| -2          | N/A   | `-qq`  | even more quiet, where supported |
| -1          | N/A   | `-q`   | quiet mode, where supported      |
| 0 (default) |       |        | default for build tool           |
| 1           |       | `-v`   | print backend output             |
| 2           | `-v`  | `-vv`  | print log messages e.g. resolving info |
| 3           | `-vv` | `-vvv` | print even more debug info       |

Settings that are not supported for a specific frontend will log a warning.
The default build frontend is `build`, which does show build backend output by
default.

Platform-specific environment variables are also available:<br/>
`CIBW_BUILD_VERBOSITY_MACOS` | `CIBW_BUILD_VERBOSITY_WINDOWS` | `CIBW_BUILD_VERBOSITY_LINUX` | `CIBW_BUILD_VERBOSITY_IOS` | `CIBW_BUILD_VERBOSITY_PYODIDE`

#### Examples

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel]
    # Ensure that the build backend output is present
    build-verbosity = 1
    ```

!!! tab examples "Environment variables"

    ```yaml
    # Ensure that the build backend output is present
    CIBW_BUILD_VERBOSITY: 1
    ```




## Command line {: #command-line}

### Options

« subprocess_run("cibuildwheel", "--help") »

### Return codes

cibuildwheel exits 0 on success, or >0 if an error occurs.

Specific error codes are defined:

- 2 means a configuration error
- 3 means no builds are selected (and [`--allow-empty`](#allow-empty) wasn't passed)
- 4 means you specified an option that has been deprecated.


## Placeholders

Some options support placeholders, like `{project}`, `{package}` or `{wheel}`, that are substituted by cibuildwheel before they are used. If, for some reason, you need to write the literal name of a placeholder, e.g. literally `{project}` in a command that would ordinarily substitute `{project}`, prefix it with a hash character - `#{project}`. This is only necessary in commands where the specific string between the curly brackets would be substituted - otherwise, strings not modified.

<style>
  /* Table of contents styling */
  .options-toc {
    display: grid;
    grid-template-columns: fit-content(20%) 1fr;
    grid-gap: 10px 20px;
    gap: 10px 20px;
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
    display: inline-block;
    margin-bottom: 3px;
  }
  .options-toc a.option code {
    font-size: 80%;
  }

  /* header styling, including the badges */
  .rst-content h3 code {
    font-size: 115%;
  }
  .rst-content h3 .badges {
    display: inline-flex;
    justify-content: right;
    flex-wrap: wrap;
    flex-direction: row;
    float: right;
    width: fit-content;
    max-width: 100%;
    gap: 2px 2px;
    position: relative;
    top: 2px;
  }
  .rst-content h3 .badges code.cmd-line, .rst-content h3 .badges code.toml, .rst-content h3 .badges code.env-var {
    font-size: 80%;
    display: inline-flex;
    flex-direction: column;
    justify-content: left;
    padding-left: 10px;
    padding-right: 10px;
    line-height: normal;
  }
  .rst-content h3 .badges code.cmd-line:before, .rst-content h3 .badges code.toml:before, .rst-content h3 .badges code.env-var:before {
    content: ' ';
    font-size: 10px;
    font-weight: bold;
    opacity: 0.5;
    display: inline-block;
    border-radius: 5px;
    margin-left: -3px;
    margin-right: -3px;
    margin-bottom: -1px;
  }
  .rst-content h3 .badges code.cmd-line:before {
    content: 'command line';
  }
  .rst-content h3 .badges code.cmd-line {
    background: rgba(224, 202, 56, 0.3);
  }
  .rst-content h3 .badges code.toml:before {
    content: 'pyproject.toml';
  }
  .rst-content h3 .badges code.toml {
    background: rgba(41, 128, 185, 0.3);
  }
  .rst-content h3 .badges code.env-var:before {
    content: 'env var';
  }
  .rst-content h3 .badges code.env-var {
    background: rgba(61, 153, 112, 0.3);
  }
  /* sidebar TOC styling */
  .toctree-l3.option a {
    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
  }
</style>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    // gather the options data
    var options = {}
    var headers = []

    $('.rst-content h3')
      .each(function (i, el) {
        var optionName = $(el).text().replace('¶', '');
        var description = $(el).next('blockquote').text()
        var header = $(el).prevAll('h2').first().text().replace('¶', '')
        var id = el.id;

        if (optionName[0].match(/[A-Z]/)) {
          // all the options are kebab-case, so this header isn't an option
          return;
        }

        if (options[header] === undefined) {
          options[header] = [];
          headers.push(header);
        }

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

    // add the option tags to each heading
    $('.rst-content h3')
      .each(function (i, el) {
        el.classList.add('option', 'clearfix');
        var optionName = $(el).text().replace('¶', '');

        var cmdLine = el.getAttribute('cmd-line');
        var envVar = el.getAttribute('env-var');
        var toml = el.getAttribute('toml');

        if (!(cmdLine || envVar || toml)) {
          return;
        }

        var badgesEl = $('<div class="badges">')
          .appendTo(el);

        // fill default value
        if (cmdLine == "cmd-line") {
          cmdLine = '--'+optionName;
        }
        if (envVar == "env-var") {
          envVar = optionName
            .split(', ')
            .map(opt => 'CIBW_'+opt.toUpperCase().replace(/-/g, '_'))
            .join(', ');
        }
        if (toml == "toml") {
          toml = optionName
        }

        if (toml) {
          badgesEl.append(' <code class="toml" title="TOML option key">'+toml+'</code>');
        }
        if (cmdLine) {
          badgesEl.append(' <code class="cmd-line" title="Command line argument">'+cmdLine+'</code>');
        }
        if (envVar) {
          badgesEl.append(' <code class="env-var" title="Environment variable">'+envVar+'</code>');
        }
      });

    $('.toctree-l3')
      .each(function (i, el) {
        var tocEntryName = $(el).text()
        var isOption = tocEntryName[0].match(/^[a-z]/);
        if (isOption) {
          $(el).addClass('option');
        }
      });
  });

</script>
