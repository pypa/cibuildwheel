## Options summary

<div class="options-toc"></div>

## Setting options

cibuildwheel is configured using environment variables, that can be set using
your CI config.

For example, to configure cibuildwheel to run tests, add the following YAML to
your CI config file:


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



## Build selection

### `CIBW_PLATFORM` {: #platform}

> Override the auto-detected target platform

Options: `auto` `linux` `macos` `windows`

Default: `auto`

`auto` will auto-detect platform using environment variables, such as `TRAVIS_OS_NAME`/`APPVEYOR`/`CIRCLECI`.

For `linux` you need Docker running, on macOS or Linux. For `macos`, you need a Mac machine, and note that this script is going to automatically install MacPython on your system, so don't run on your development machine. For `windows`, you need to run in Windows, and `cibuildwheel` will install required versions of Python to `C:\cibw\python` using NuGet.

This option can also be set using the [command-line option](#command-line) `--platform`.


### `CIBW_BUILD`, `CIBW_SKIP` {: #build-skip}

> Choose the Python versions to build

Space-separated list of builds to build and skip. Each build has an identifier like `cp27-manylinux_x86_64` or `cp35-macosx_x86_64` - you can list specific ones to build and `cibuildwheel` will only build those, and/or list ones to skip and `cibuildwheel` won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `CIBW_BUILD` and does not match `CIBW_SKIP` will be built.

When setting the options, you can use shell-style globbing syntax, as per [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) with the addition of curly bracket syntax `{option1,option2}`, provided by [`bracex`](https://pypi.org/project/bracex/). All the build identifiers supported by cibuildwheel are shown below:

<div class="build-id-table-marker"></div>

|              | macOS                                                               | Windows                       | Manylinux Intel                               | Manylinux Other                                                            |
|--------------|---------------------------------------------------------------------|-------------------------------|-----------------------------------------------|----------------------------------------------------------------------------|
| Python 2.7   | cp27-macosx_x86_64                                                  | cp27-win_amd64<br/>cp27-win32 | cp27-manylinux_x86_64<br/>cp27-manylinux_i686 |                                                                            |
| Python 3.5   | cp35-macosx_x86_64                                                  | cp35-win_amd64<br/>cp35-win32 | cp35-manylinux_x86_64<br/>cp35-manylinux_i686 | cp35-manylinux_aarch64<br/>cp35-manylinux_ppc64le<br/>cp35-manylinux_s390x |
| Python 3.6   | cp36-macosx_x86_64                                                  | cp36-win_amd64<br/>cp36-win32 | cp36-manylinux_x86_64<br/>cp36-manylinux_i686 | cp36-manylinux_aarch64<br/>cp36-manylinux_ppc64le<br/>cp36-manylinux_s390x |
| Python 3.7   | cp37-macosx_x86_64                                                  | cp37-win_amd64<br/>cp37-win32 | cp37-manylinux_x86_64<br/>cp37-manylinux_i686 | cp37-manylinux_aarch64<br/>cp37-manylinux_ppc64le<br/>cp37-manylinux_s390x |
| Python 3.8   | cp38-macosx_x86_64                                                  | cp38-win_amd64<br/>cp38-win32 | cp38-manylinux_x86_64<br/>cp38-manylinux_i686 | cp38-manylinux_aarch64<br/>cp38-manylinux_ppc64le<br/>cp38-manylinux_s390x |
| Python 3.9   | cp39-macosx_x86_64<br/>cp39-macosx_universal2<br/>cp39-macosx_arm64 | cp39-win_amd64<br/>cp39-win32 | cp39-manylinux_x86_64<br/>cp39-manylinux_i686 | cp39-manylinux_aarch64<br/>cp39-manylinux_ppc64le<br/>cp39-manylinux_s390x |
| PyPy2.7 v7.3 | pp27-macosx_x86_64                                                  |                    pp27-win32 | pp27-manylinux_x86_64                         |                                                                            |
| PyPy3.6 v7.3 | pp36-macosx_x86_64                                                  |                    pp36-win32 | pp36-manylinux_x86_64                         |                                                                            |
| PyPy3.7 v7.3 | pp37-macosx_x86_64                                                  |                    pp37-win32 | pp37-manylinux_x86_64                         |                                                                            |


The list of supported and currently selected build identifiers can also be retrieved by passing the `--print-build-identifiers` flag to `cibuildwheel`.
The format is `python_tag-platform_tag`, with tags similar to those in [PEP 425](https://www.python.org/dev/peps/pep-0425/#details).

For CPython, the minimally supported macOS version is 10.9; for PyPy 2.7 and PyPy 3.6/3.7, respectively macOS 10.7 and 10.13 or higher is required.

#### Examples

```yaml
# Only build on Python 3.6
CIBW_BUILD: cp36-*

# Skip building on Python 2.7 on the Mac
CIBW_SKIP: cp27-macosx_x86_64

# Skip building on Python 3.8 on the Mac
CIBW_SKIP: cp38-macosx_x86_64

# Skip building on Python 2.7 on all platforms
CIBW_SKIP: cp27-*

# Skip Python 2.7 on Windows
CIBW_SKIP: cp27-win*

# Skip Python 2.7 on 32-bit Windows
CIBW_SKIP: cp27-win32

# Skip Python 2.7 and Python 3.5
CIBW_SKIP: cp27-* cp35-*

# Skip Python 3.6 on Linux
CIBW_SKIP: cp36-manylinux*

# Only build on Python 3 (ready for 3.10 when it comes) and skip 32-bit builds
CIBW_BUILD: {cp,pp}3*-*
CIBW_SKIP: "*-win32 *-manylinux_i686"

# Only build PyPy and CPython 3
CIBW_BUILD: pp* cp3*-*

# Disable building PyPy wheels on all platforms
CIBW_SKIP: pp*
```

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

### `CIBW_ARCHS` {: #archs}
> Change the architectures built on your machine by default.

A space-separated list of architectures to build.

On macOS, this option can be used to cross-compile between `x86_64`,
`universal2` and `arm64` for Apple Silicon support.

On Linux, this option can be used to build non-native architectures under
emulation. See [this guide](faq.md#emulation) for more information.

Options:

- Linux: `x86_64` `i686` `aarch64` `ppc64le` `s390x`
- macOS: `x86_64` `arm64` `universal2`
- Windows: `AMD64` `x86`
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
| macOS / Intel | `x86_64` | `x86_64` | `x86_64` |  |
| macOS / Apple Silicon | `arm64` | `arm64` `universal2` | `arm64` `universal2`|  |

If not listed above, `auto` is the same as `native`.

[setup-qemu-action]: https://github.com/docker/setup-qemu-action
[binfmt]: https://hub.docker.com/r/tonistiigi/binfmt

Platform-specific variants also available:<br/>
 `CIBW_ARCHS_MACOS` | `CIBW_ARCHS_WINDOWS` | `CIBW_ARCHS_LINUX`

This option can also be set using the [command-line option](#command-line) `--archs`.

#### Examples

```yaml
# Build `universal2` and `arm64` wheels on an Intel runner.
# Note that the `arm64` wheel and the `arm64` part of the `universal2`
# wheel cannot be tested in this configuration.
CIBW_ARCHS_MACOS: "x86_64 universal2 arm64"

# On an Linux Intel runner with qemu installed, build Intel and ARM wheels
CIBW_ARCHS_LINUX: "auto aarch64"
```


###  `CIBW_PROJECT_REQUIRES_PYTHON` {: #requires-python}
> Manually set the Python compatibility of your project

By default, cibuildwheel reads your package's Python compatibility from
`pyproject.toml` following [PEP621](https://www.python.org/dev/peps/pep-0621/)
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
    Rather than using this option, it's recommended you set
    `project.requires-python` in `pyproject.toml` instead:
    Example `pyproject.toml`:

        [project]
        requires-python = ">=3.6"

        # Aside - in pyproject.toml you should always specify minimal build
        # system options, like this:

        [build-system]
        requires = ["setuptools>=42", "wheel"]
        build-backend = "setuptools.build_meta"


    Currently, setuptools has not yet added support for reading this value from
    pyproject.toml yet, and so does not copy it to Requires-Python in the wheel
    metadata. This mechanism is used by `pip` to scan through older versions of
    your package until it finds a release compatible with the curernt version
    of Python compatible when installing, so it is an important value to set if
    you plan to drop support for a version of Python in the future.

    If you don't want to list this value twice, you can also use the setuptools
    specific location in `setup.cfg` and cibuildwheel will detect it from
    there. Example `setup.cfg`:

        [options]
        python_requires = ">=3.6"

#### Examples

```yaml
CIBW_PROJECT_REQUIRES_PYTHON: ">=3.6"
```

## Build customization

### `CIBW_ENVIRONMENT` {: #environment}
> Set environment variables needed during the build

A space-separated list of environment variables to set during the build. Bash syntax should be used, even on Windows.

You must set this variable to pass variables to Linux builds (since they execute in a Docker container). It also works for the other platforms.

You can use `$PATH` syntax to insert other variables, or the `$(pwd)` syntax to insert the output of other shell commands.

To specify more than one environment variable, separate the assignments by spaces.

Platform-specific variants also available:<br/>
`CIBW_ENVIRONMENT_MACOS` | `CIBW_ENVIRONMENT_WINDOWS` | `CIBW_ENVIRONMENT_LINUX`

#### Examples
```yaml
# Set some compiler flags
CIBW_ENVIRONMENT: "CFLAGS='-g -Wall' CXXFLAGS='-Wall'"

# Append a directory to the PATH variable (this is expanded in the build environment)
CIBW_ENVIRONMENT: "PATH=$PATH:/usr/local/bin"

# Set BUILD_TIME to the output of the `date` command
CIBW_ENVIRONMENT: "BUILD_TIME=$(date)"

# Supply options to `pip` to affect how it downloads dependencies
CIBW_ENVIRONMENT: "PIP_EXTRA_INDEX_URL=https://pypi.myorg.com/simple"

# Set two flags
CIBW_ENVIRONMENT: "BUILD_TIME=$(date) SAMPLE_TEXT=\"sample text\""
```

!!! note
    `cibuildwheel` always defines the environment variable `CIBUILDWHEEL=1`. This can be useful for [building wheels with optional extensions](faq.md#building-packages-with-optional-c-extensions).

### `CIBW_BEFORE_ALL` {: #before-all}
> Execute a shell command on the build system before any wheels are built.

Shell command to prepare a common part of the project (e.g. build or install libraries which does not depend on the specific version of Python).

This option is very useful for the Linux build, where builds take place in isolated Docker containers managed by cibuildwheel. This command will run inside the container before the wheel builds start. Note, if you're building both x86_64 and i686 wheels (the default), your build uses two different Docker images. In that case, this command will execute twice - once per build container.

The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by `cibuildwheel`.

On Windows and macOS, the version of Python available inside `CIBW_BEFORE_ALL` is whatever is available on the host machine. On Linux, a modern Python version is available on PATH.

Platform-specific variants also available:<br/>
 `CIBW_BEFORE_ALL_MACOS` | `CIBW_BEFORE_ALL_WINDOWS` | `CIBW_BEFORE_ALL_LINUX`

#### Examples
```yaml
# build third party library
CIBW_BEFORE_ALL: make -C third_party_lib

# install system library
CIBW_BEFORE_ALL_LINUX: yum install -y libffi-dev
```

### `CIBW_BEFORE_BUILD` {: #before-build}
> Execute a shell command preparing each wheel's build

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), instead of using this command, we recommend adding requirements to a pyproject.toml file. This is reproducible, and users who do not get your wheels (such as Alpine or ClearLinux users) will still benefit.

The active Python binary can be accessed using `python`, and pip with `pip`; `cibuildwheel` makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by `cibuildwheel`.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific variants also available:<br/>
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX`

#### Examples
```yaml
# install something required for the build (you might want to use pyproject.toml instead)
CIBW_BEFORE_BUILD: pip install pybind11

# chain commands using &&
CIBW_BEFORE_BUILD_LINUX: yum install -y libffi-dev && make clean

# run a script that's inside your project
CIBW_BEFORE_BUILD: bash scripts/prepare_for_build.sh

# if cibuildwheel is called with a package_dir argument, it's available as {package}
CIBW_BEFORE_BUILD: "{package}/script/prepare_for_build.sh"
```

!!! note
    If you need dependencies installed for the build, we recommend using
    `pyproject.toml`. This is an example `pyproject.toml` file:

        [build-system]
        requires = [
            "setuptools>=42",
            "wheel",
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
> Execute a shell command to repair each (non-pure Python) built wheel

Default:

- on Linux: `'auditwheel repair -w {dest_dir} {wheel}'`
- on macOS: `'delocate-listdeps {wheel} && delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}'`
- on Windows: `''`

A shell command to repair a built wheel by copying external library dependencies into the wheel tree and relinking them.
The command is run on each built wheel (except for pure Python ones) before testing it.

The following placeholders must be used inside the command and will be replaced by `cibuildwheel`:

- `{wheel}` for the absolute path to the built wheel
- `{dest_dir}` for the absolute path of the directory where to create the repaired wheel
- `{delocate_archs}` (macOS only) comma-separated list of architectures in the wheel.

The command is run in a shell, so you can run multiple commands like `cmd1 && cmd2`.

Platform-specific variants also available:<br/>
`CIBW_REPAIR_WHEEL_COMMAND_MACOS` | `CIBW_REPAIR_WHEEL_COMMAND_WINDOWS` | `CIBW_REPAIR_WHEEL_COMMAND_LINUX`

#### Examples

```yaml
# don't repair macOS wheels
CIBW_REPAIR_WHEEL_COMMAND_MACOS: ""

# pass the `--lib-sdir .` flag to auditwheel on Linux
CIBW_REPAIR_WHEEL_COMMAND_LINUX: "auditwheel repair --lib-sdir . -w {dest_dir} {wheel}"
```


### `CIBW_MANYLINUX_X86_64_IMAGE`, `CIBW_MANYLINUX_I686_IMAGE`, `CIBW_MANYLINUX_PYPY_X86_64_IMAGE`, `CIBW_MANYLINUX_AARCH64_IMAGE`, `CIBW_MANYLINUX_PPC64LE_IMAGE`, `CIBW_MANYLINUX_S390X_IMAGE` {: #manylinux-image}
> Specify alternative manylinux docker images

An alternative Docker image to be used for building [`manylinux`](https://github.com/pypa/manylinux) wheels. `cibuildwheel` will then pull these instead of the default images, [`quay.io/pypa/manylinux2010_x86_64`](https://quay.io/pypa/manylinux2010_x86_64), [`quay.io/pypa/manylinux2010_i686`](https://quay.io/pypa/manylinux2010_i686), [`pypywheels/manylinux2010-pypy_x86_64`](https://hub.docker.com/r/pypywheels/manylinux2010-pypy_x86_64), [`quay.io/pypa/manylinux2014_aarch64`](https://quay.io/pypa/manylinux2014_aarch64), [`quay.io/pypa/manylinux2014_ppc64le`](https://quay.io/pypa/manylinux2014_ppc64le), and [`quay.io/pypa/manylinux2014_s390x`](https://quay.io/pypa/manylinux2010_s390x).

The value of this option can either be set to `manylinux1`, `manylinux2010`, `manylinux2014` or `manylinux_2_24` to use a pinned version of the [official `manylinux` images](https://github.com/pypa/manylinux) and [PyPy `manylinux` images](https://github.com/pypy/manylinux). Alternatively, set these options to any other valid Docker image name. Note that for PyPy, only the official `manylinux2010` image is currently available. For architectures other
than x86 (x86\_64 and i686) `manylinux2014` or `manylinux_2_24` must be used because the first version of the manylinux specification that supports additional architectures is `manylinux2014`.

Beware to specify a valid Docker image that can be used in the same way as the official, default Docker images: all necessary Python and pip versions need to be present in `/opt/python/`, and the `auditwheel` tool needs to be present for `cibuildwheel` to work. Apart from that, the architecture and relevant shared system libraries need to be manylinux1-, manylinux2010- or manylinux2014-compatible in order to produce valid `manylinux1`/`manylinux2010`/`manylinux2014`/`manylinux_2_24` wheels (see [pypa/manylinux on GitHub](https://github.com/pypa/manylinux), [PEP 513](https://www.python.org/dev/peps/pep-0513/), [PEP 571](https://www.python.org/dev/peps/pep-0571/), [PEP 599](https://www.python.org/dev/peps/pep-0599/) and  [PEP 600](https://www.python.org/dev/peps/pep-0600/)  for more details).

Note that `auditwheel` detects the version of the `manylinux` standard in the Docker image through the `AUDITWHEEL_PLAT` environment variable, as `cibuildwheel` has no way of detecting the correct `--plat` command line argument to pass to `auditwheel` for a custom image. If a Docker image does not correctly set this `AUDITWHEEL_PLAT` environment variable, the `CIBW_ENVIRONMENT` option can be used to do so (e.g., `CIBW_ENVIRONMENT='AUDITWHEEL_PLAT="manylinux2010_$(uname -m)"'`).

Note that `manylinux2014`/`manylinux_2_24` don't support builds with Python 2.7 - when building with `manylinux2014`/`manylinux_2_24`, skip Python 2.7 using `CIBW_SKIP` (see example below).

#### Examples

```yaml
# build using the manylinux1 image to ensure manylinux1 wheels are produced
# skip PyPy, since there is no PyPy manylinux1 image
CIBW_MANYLINUX_X86_64_IMAGE: manylinux1
CIBW_MANYLINUX_I686_IMAGE: manylinux1
CIBW_SKIP: pp*

# build using the manylinux2014 image
CIBW_MANYLINUX_X86_64_IMAGE: manylinux2014
CIBW_MANYLINUX_I686_IMAGE: manylinux2014
CIBW_SKIP: cp27-manylinux*

# build using the latest manylinux2010 release, instead of the cibuildwheel
# pinned version
CIBW_MANYLINUX_X86_64_IMAGE: quay.io/pypa/manylinux2010_x86_64:latest
CIBW_MANYLINUX_I686_IMAGE: quay.io/pypa/manylinux2010_i686:latest

# build using a different image from the docker registry
CIBW_MANYLINUX_X86_64_IMAGE: dockcross/manylinux-x64
CIBW_MANYLINUX_I686_IMAGE: dockcross/manylinux-x86
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
    `./constraints-python27.txt` on Python 2.7, or fallback to
    `./constraints.txt` if that's not found.

Platform-specific variants also available:<br/>
`CIBW_DEPENDENCY_VERSIONS_MACOS` | `CIBW_DEPENDENCY_VERSIONS_WINDOWS`

!!! note
    This option does not affect the tools used on the Linux build - those versions
    are bundled with the manylinux image that cibuildwheel uses. To change
    dependency versions on Linux, use the [CIBW_MANYLINUX_*](#manylinux-image)
    options.

#### Examples

```yaml
# use tools versions that are bundled with cibuildwheel (this is the default)
CIBW_DEPENDENCY_VERSIONS: pinned

# use the latest versions available on PyPI
CIBW_DEPENDENCY_VERSIONS: latest

# use your own pip constraints file
CIBW_DEPENDENCY_VERSIONS: ./constraints.txt
```


## Testing

### `CIBW_TEST_COMMAND` {: #test-command}
> Execute a shell command to test each built wheel

Shell command to run tests after the build. The wheel will be installed
automatically and available for import from the tests. To ensure the wheel is
imported by your tests (instead of your source copy), tests are run from a
different directory. Use the placeholders `{project}` and `{package}` when
specifying paths in your project. If this variable is not set, your wheel will
not be installed after building.

- `{project}` is an absolute path to the project root - the working directory
  where cibuildwheel was called.
- `{package}` is the path to the package being built - the `package_dir`
  argument supplied to cibuildwheel on the command line.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific variants also available:<br/>
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX`

#### Examples

```yaml
# run the project tests against the installed wheel using `nose`
CIBW_TEST_COMMAND: nosetests {project}/tests

# run the package tests using `pytest`
CIBW_TEST_COMMAND: pytest {package}/tests

# trigger an install of the package, but run nothing of note
CIBW_TEST_COMMAND: "echo Wheel installed"
```


### `CIBW_BEFORE_TEST` {: #before-test}
> Execute a shell command before testing each wheel

A shell command to run in **each** test virtual environment, before your wheel is installed and tested. This is useful if you need to install a non pip package, change values of environment variables
or perform multi step pip installation (e.g. installing `scikit-build` or `cython` before install test package)

The active Python binary can be accessed using `python`, and pip with `pip`; `cibuildwheel` makes sure the right version of Python and pip will be executed. The placeholder `{package}` can be used here; it will be replaced by the path to the package being built by `cibuildwheel`.

The command is run in a shell, so you can write things like `cmd1 && cmd2`.

Platform-specific variants also available:<br/>
 `CIBW_BEFORE_TEST_MACOS` | `CIBW_BEFORE_TEST_WINDOWS` | `CIBW_BEFORE_TEST_LINUX`

#### Examples
```yaml
# install test dependencies with overwritten environment variables.
CIBW_BEFORE_TEST: CC=gcc CXX=g++ pip install -r requirements.txt

# chain commands using &&
CIBW_BEFORE_TEST: rm -rf ./data/cache && mkdir -p ./data/cache

# install non pip python package
CIBW_BEFORE_TEST: cd some_dir; ./configure; make; make install

# install python packages that are required to install test dependencies
CIBW_BEFORE_TEST: pip install cmake scikit-build
```


### `CIBW_TEST_REQUIRES` {: #test-requires}
> Install Python dependencies before running the tests

Space-separated list of dependencies required for running the tests.

Platform-specific variants also available:<br/>
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX`

#### Examples

```yaml
# install pytest before running CIBW_TEST_COMMAND
CIBW_TEST_REQUIRES: pytest

# install specific versions of test dependencies
CIBW_TEST_REQUIRES: nose==1.3.7 moto==0.4.31
```


### `CIBW_TEST_EXTRAS` {: #test-extras}
> Install your wheel for testing using `extras_require`

Comma-separated list of
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
options that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`CIBW_TEST_REQUIRES` if they are already defined in `setup.py` or
`setup.cfg`.

Platform-specific variants also available:<br/>
`CIBW_TEST_EXTRAS_MACOS` | `CIBW_TEST_EXTRAS_WINDOWS` | `CIBW_TEST_EXTRAS_LINUX`

#### Examples

```yaml
# will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`
CIBW_TEST_EXTRAS: test,qt
```

### `CIBW_TEST_SKIP` {: #test-skip}
> Skip running tests on some builds

This will skip testing on any identifiers that match the given skip patterns (see [`CIBW_SKIP`](#build-skip)). This can be used to mask out tests for wheels that have missing dependencies upstream that are slow or hard to build, or to mask up slow tests on emulated architectures.

With macOS `universal2` wheels, you can also skip the the individual archs inside the wheel using an `:arch` suffix. For example, `cp39-macosx_universal2:x86_64` or `cp39-macosx_universal2:arm64`.

#### Examples

```yaml
# Will avoid testing on emulated architectures
CIBW_TEST_SKIP: "*-manylinux_{aarch64,ppc64le,s390x}"

# Skip trying to test arm64 builds on Intel Macs
CIBW_TEST_SKIP: "*-macosx_arm64 *-macosx_universal2:arm64"
```


## Other

### `CIBW_BUILD_VERBOSITY` {: #build-verbosity}
> Increase/decrease the output of pip wheel

An number from 1 to 3 to increase the level of verbosity (corresponding to invoking pip with `-v`, `-vv`, and `-vvv`), between -1 and -3 (`-q`, `-qq`, and `-qqq`), or just 0 (default verbosity). These flags are useful while debugging a build when the output of the actual build invoked by `pip wheel` is required.

Platform-specific variants also available:<br/>
`CIBW_BUILD_VERBOSITY_MACOS` | `CIBW_BUILD_VERBOSITY_WINDOWS` | `CIBW_BUILD_VERBOSITY_LINUX`

#### Examples

```yaml
# increase pip debugging output
CIBW_BUILD_VERBOSITY: 1
```


## Command line options {: #command-line}

```text
usage: cibuildwheel [-h] [--platform {auto,linux,macos,windows}]
                    [--archs ARCHS] [--output-dir OUTPUT_DIR]
                    [--print-build-identifiers] [--allow-empty]
                    [package_dir]

Build wheels for all the platforms.

positional arguments:
  package_dir           Path to the package that you want wheels for. Must be
                        a subdirectory of the working directory. When set, the
                        working directory is still considered the 'project'
                        and is copied into the Docker container on Linux.
                        Default: the working directory.

optional arguments:
  -h, --help            show this help message and exit
  --platform {auto,linux,macos,windows}
                        Platform to build for. For "linux" you need docker
                        running, on Mac or Linux. For "macos", you need a Mac
                        machine, and note that this script is going to
                        automatically install MacPython on your system, so
                        don't run on your development machine. For "windows",
                        you need to run in Windows, and it will build and test
                        for all versions of Python. Default: auto.
  --archs ARCHS         Comma-separated list of CPU architectures to build
                        for. When set to 'auto', builds the architectures
                        natively supported on this machine. Set this option to
                        build an architecture via emulation, for example,
                        using binfmt_misc and QEMU. Default: auto. Choices:
                        auto, native, all, x86_64, i686, aarch64, ppc64le,
                        s390x, x86, AMD64
  --output-dir OUTPUT_DIR
                        Destination folder for the wheels.
  --print-build-identifiers
                        Print the build identifiers matched by the current
                        invocation and exit.
  --allow-empty         Do not report an error code if the build does not
                        match any wheels.
```

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
        return !!$(el).text().match(/(^([A-Z0-9, _]| and )+)¶$/);
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
        var url = 'https://cibuildwheel.readthedocs.io/en/stable/options/#'+option.id;
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
