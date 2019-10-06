### Setting options

cibuildwheel is configured using environment variables, that can be set using 
your CI config.

For example, to configure cibuildwheel to run tests, add the following YAML to
your CI config file:

> .travis.yml ([docs](https://docs.travis-ci.com/user/environment-variables/))
```yaml
env:
  global:
    - CIBW_TEST_REQUIRES=nose
    - CIBW_TEST_COMMAND="nosetests {project}/tests"
```

> appveyor.yml ([docs](https://www.appveyor.com/docs/build-configuration/#environment-variables))
```yaml
environment:
  global:
    CIBW_TEST_REQUIRES: nose
    CIBW_TEST_COMMAND: "nosetests {project}\\tests"
```

> .circleci/config.yml ([docs](https://circleci.com/docs/2.0/configuration-reference/#environment))
```yaml
jobs:
  job_name:
    environment:
      CIBW_TEST_REQUIRES: nose
      CIBW_TEST_COMMAND: "nosetests {project}/tests"
```

> azure-pipelines.yml ([docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/variables))
```yaml
variables:
  CIBW_TEST_REQUIRES: nose
  CIBW_TEST_COMMAND: "nosetests {project}/tests"
```

## 🚩Build selection

### CIBW_PLATFORM - Override the auto-detected target platform {: #platform}

Options: `auto` `linux` `macos` `windows`

Default: `auto`

`auto` will auto-detect platform using environment variables, such as `TRAVIS_OS_NAME`/`APPVEYOR`/`CIRCLECI`.

For `linux` you need Docker running, on Mac or Linux. For `macos`, you need a Mac machine, and note that this script is going to automatically install MacPython on your system, so don't run on your development machine. For `windows`, you need to run in Windows, and it will build and test for all versions of Python at `C:\PythonXX[-x64]`.

### CIBW_BUILD, CIBW_SKIP - Choose the Python versions to build {: #build-skip}

Space-separated list of builds to build and skip. Each build has an identifier like `cp27-manylinux1_x86_64` or `cp34-macosx_10_6_intel` - you can list specific ones to build and `cibuildwheel` will only build those, and/or list ones to skip and `cibuildwheel` won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `CIBW_BUILD` and does not match `CIBW_SKIP` will be built.

The format is `python_tag-platform_tag`. The tags are as defined in [PEP 0425](https://www.python.org/dev/peps/pep-0425/#details).

Python tags look like `cp27` `cp34` `cp35` `cp36` `cp37`

Platform tags look like `macosx_10_6_intel` `manylinux1_x86_64` `manylinux1_i686` `win32` `win_amd64`

You can also use shell-style globbing syntax (as per `fnmatch`) 

Examples:

- Only build on Python 3.6: `CIBW_BUILD=cp36-*`
- Skip building on Python 2.7 on the Mac: `CIBW_SKIP=cp27-macosx_10_6_intel`
- Skip building on Python 2.7 on all platforms: `CIBW_SKIP=cp27-*`
- Skip Python 2.7 on Windows: `CIBW_SKIP=cp27-win*`
- Skip Python 2.7 on 32-bit Windows: `CIBW_SKIP=cp27-win32`
- Skip Python 3.4 and Python 3.5: `CIBW_SKIP=cp34-* cp35-*`
- Skip Python 3.6 on Linux: `CIBW_SKIP=cp36-manylinux*`
- Only build on Python 3 and skip 32-bit builds: `CIBW_BUILD=cp3?-*` and `CIBW_SKIP=*-win32 *-manylinux1_i686`

## 🌎 Build environment

### CIBW_ENVIRONMENT - Set environment variables needed during the build {: #environment}

A space-separated list of environment variables to set during the build. Bash syntax should be used (even on Windows!).

You must set this variable to pass variables to Linux builds (since they execute in a Docker container). It also works for the other platforms.

You can use `$PATH` syntax to insert other variables, or the `$(pwd)` syntax to insert the output of other shell commands.

Example: `CFLAGS="-g -Wall" CXXFLAGS="-Wall"`  
Example: `PATH=$PATH:/usr/local/bin`  
Example: `BUILD_TIME="$(date)"`  
Example: `PIP_EXTRA_INDEX_URL="https://pypi.myorg.com/simple"`  

Platform-specific variants also available:
`CIBW_ENVIRONMENT_MACOS` | `CIBW_ENVIRONMENT_WINDOWS` | `CIBW_ENVIRONMENT_LINUX`

In addition to the above, `cibuildwheel` always defines the environment variable `CIBUILDWHEEL=1`. This can be useful for [building wheels with optional extensions](https://github.com/joerick/cibuildwheel/wiki/Building-packages-with-optional-C-extensions).

### CIBW_BEFORE_BUILD - Execute a shell command preparing each wheel's build {: #before-build}

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), set this to `pip install .`, and the dependencies will be installed automatically by pip. However, this means your package will be built twice - if your package takes a long time to build, you might wish to manually list the dependencies here instead.

The active Python binary can be accessed using `python`, and pip with `pip`; `cibuildwheel` makes sure the right version of Python and pip will be executed. `{project}` can be used as a placeholder for the absolute path to the project's root.

Example: `pip install .`  
Example: `pip install pybind11`  
Example: `yum install -y libffi-dev && pip install .`

Platform-specific variants also available:  
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX`

### CIBW_MANYLINUX1_X86_64_IMAGE, CIBW_MANYLINUX1_I686_IMAGE - Specify alternative manylinux1 x86_64 docker images {: #manylinux-image}

An alternative docker image to be used for building [`manylinux1`](https://github.com/pypa/manylinux) wheels. `cibuildwheel` will then pull these instead of the official images, [`quay.io/pypa/manylinux1_x86_64`](https://quay.io/pypa/manylinux1_i686) and [`quay.io/pypa/manylinux1_i686`](https://quay.io/pypa/manylinux1_i686).

Beware to specify a valid docker image that can be used the same as the official, default docker images: all necessary Python and pip versions need to be present in `/opt/python/`, and the `auditwheel` tool needs to be present for `cibuildwheel` to work. Apart from that, the architecture and relevant shared system libraries need to be manylinux1-compatible in order to produce valid `manylinux1` wheels (see https://github.com/pypa/manylinux and [PEP 513](https://www.python.org/dev/peps/pep-0513/) for more details).

Example: `dockcross/manylinux-x64`  
Example: `dockcross/manylinux-x86`

## 🔬 Testing

### CIBW_TEST_COMMAND - Execute a shell command to test all built wheels {: #test-command}

Shell command to run tests after the build. The wheel will be installed automatically and available for import from the tests. `{project}` can be used as a placeholder for the absolute path to the project's root and will be replaced by `cibuildwheel`.

On Linux and Mac, the command runs in a shell, so you can write things like `cmd1 && cmd2`. 

Example: `nosetests {project}/tests`

Platform-specific variants also available:
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX`

### CIBW_TEST_REQUIRES - Install Python dependencies before running the tests {: #test-requires}

Space-separated list of dependencies required for running the tests.

Example: `pytest`  
Example: `nose==1.3.7 moto==0.4.31`

Platform-specific variants also available:
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX`

### CIBW_TEST_EXTRAS - Install your wheel for testing using `extras_require` {: #test-extras}

Comma-separated list of
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
options that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`CIBW_TEST_REQUIRES` if they are already defined in `setup.py` or
`setup.cfg`.

Example: `test,qt` (will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`)


Platform-specific variants also available:
`CIBW_TEST_EXTRAS_MACOS` | `CIBW_TEST_EXTRAS_WINDOWS` | `CIBW_TEST_EXTRAS_LINUX`

## 💭 Other

### CIBW_BUILD_VERBOSITY - Increase/decrease the output of pip wheel

An number from 1 to 3 to increase the level of verbosity (corresponding to invoking pip with `-v`, `-vv`, and `-vvv`), between -1 and -3 (`-q`, `-qq`, and `-qqq`), or just 0 (default verbosity). These flags are useful while debugging a build when the output of the actual build invoked by `pip wheel` is required.

Platform-specific variants also available:
`CIBW_BUILD_VERBOSITY_MACOS` | `CIBW_BUILD_VERBOSITY_WINDOWS` | `CIBW_BUILD_VERBOSITY_LINUX`

## Command line options

```text
usage: cibuildwheel [-h] [--platform {auto,linux,macos,windows}]
                    [--output-dir OUTPUT_DIR] [--print-build-identifiers]
                    [project_dir]
    
Build wheels for all the platforms.

positional arguments:
  project_dir           Path to the project that you want wheels for.
                        Default: the current directory.

optional arguments:
  -h, --help            show this help message and exit
  --platform {auto,linux,macos,windows}
                        Platform to build for. For "linux" you need docker
                        running, on Mac or Linux. For "macos", you need a Mac
                        machine, and note that this script is going to
                        automatically install MacPython on your system, so
                        don't run on your development machine. For "windows",
                        you need to run in Windows, and it will build and test
                        for all versions of Python at C:\PythonXX[-x64].
  --output-dir OUTPUT_DIR
                        Destination folder for the wheels.
  --print-build-identifiers
                        Print the build identifiers matched by the current
                        invocation and exit.

```

<style>
  .cibw-option-header {
    margin-top: 5px;
    /* border-bottom: 1px solid rgba(0, 0, 0, 0.05); */
  }
  .cibw-option-header:hover {
    background-color: transparent !important;
  }
  .cibw-option-name {
    display: block;
    font-weight: bold;
  }
  .cibw-option-description {
    font-size: 0.9em;
  }
</style>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    // add styling classes to the toc-tree elements
    $('.wy-menu-vertical li.current a').each(function(i, el) {
      var $el = $(el);
      $el.html( $el.text().replace(
        /(^[A-Z0-9, _]+) - (.*)$/,
        '<div class="cibw-option-name">$1</div><div class="cibw-option-description">$2</div>')
      );
    })
    
    // add styling classes to the emoji headers
    $('.wy-menu-vertical li.current a').each(function(i, el) {
      var $el = $(el);
      var text = $el.text();
      var emojiStartRegex = /^(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/

      if (text.match(emojiStartRegex)) {
        $el.addClass('cibw-option-header')
      }
    })
  })
</script>
