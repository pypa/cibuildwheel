## Options summary

<div class="options-toc"></div>

## Setting options

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

## Build selection

### CIBW_PLATFORM {: #platform}
> Override the auto-detected target platform

Options: `auto` `linux` `macos` `windows`

Default: `auto`

`auto` will auto-detect platform using environment variables, such as `TRAVIS_OS_NAME`/`APPVEYOR`/`CIRCLECI`.

For `linux` you need Docker running, on Mac or Linux. For `macos`, you need a Mac machine, and note that this script is going to automatically install MacPython on your system, so don't run on your development machine. For `windows`, you need to run in Windows, and it will build and test for all versions of Python at `C:\PythonXX[-x64]`.

### CIBW_BUILD, CIBW_SKIP {: #build-skip}

> Choose the Python versions to build

Space-separated list of builds to build and skip. Each build has an identifier like `cp27-manylinux_x86_64` or `cp35-macosx_10_6_intel` - you can list specific ones to build and `cibuildwheel` will only build those, and/or list ones to skip and `cibuildwheel` won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `CIBW_BUILD` and does not match `CIBW_SKIP` will be built.

The format is `python_tag-platform_tag`. The tags are similar but not identical to the ones defined in [PEP 425](https://www.python.org/dev/peps/pep-0425/#details).

Python tags look like `cp27` `cp34` `cp35` `cp36` `cp37` `cp38`

Platform tags look like `macosx_10_6_intel` `macosx_10_9_x86_64` `manylinux_x86_64` `manylinux_i686` `win32` `win_amd64`

You can also use shell-style globbing syntax (as per `fnmatch`).

The list of supported and currently selected build identifiers can be retrieved by passing the `--print-build-identifiers` flag to `cibuildwheel`.

Examples:

- Only build on Python 3.6: `CIBW_BUILD=cp36-*`
- Skip building on Python 2.7 on the Mac: `CIBW_SKIP=cp27-macosx_10_6_intel`
- Skip building on Python 3.8 on the Mac: `CIBW_SKIP=cp38-macosx_10_9_x86_64`
- Skip building on Python 2.7 on all platforms: `CIBW_SKIP=cp27-*`
- Skip Python 2.7 on Windows: `CIBW_SKIP=cp27-win*`
- Skip Python 2.7 on 32-bit Windows: `CIBW_SKIP=cp27-win32`
- Skip Python 2.7 and Python 3.5: `CIBW_SKIP=cp27-* cp35-*`
- Skip Python 3.6 on Linux: `CIBW_SKIP=cp36-manylinux*`
- Only build on Python 3 and skip 32-bit builds: `CIBW_BUILD=cp3?-*` and `CIBW_SKIP=*-win32 *-manylinux_i686`

## Build environment

### CIBW_ENVIRONMENT {: #environment}
> Set environment variables needed during the build

A space-separated list of environment variables to set during the build. Bash syntax should be used (even on Windows!).

You must set this variable to pass variables to Linux builds (since they execute in a Docker container). It also works for the other platforms.

You can use `$PATH` syntax to insert other variables, or the `$(pwd)` syntax to insert the output of other shell commands.

Example: `CFLAGS="-g -Wall" CXXFLAGS="-Wall"`\
Example: `PATH=$PATH:/usr/local/bin`\
Example: `BUILD_TIME="$(date)"`\
Example: `PIP_EXTRA_INDEX_URL="https://pypi.myorg.com/simple"`

Platform-specific variants also available:
`CIBW_ENVIRONMENT_MACOS` | `CIBW_ENVIRONMENT_WINDOWS` | `CIBW_ENVIRONMENT_LINUX`

In addition to the above, `cibuildwheel` always defines the environment variable `CIBUILDWHEEL=1`. This can be useful for [building wheels with optional extensions](https://github.com/joerick/cibuildwheel/wiki/Building-packages-with-optional-C-extensions).

### CIBW_BEFORE_BUILD {: #before-build}
> Execute a shell command preparing each wheel's build

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), set this to `pip install .`, and the dependencies will be installed automatically by pip. However, this means your package will be built twice - if your package takes a long time to build, you might wish to manually list the dependencies here instead.

The active Python binary can be accessed using `python`, and pip with `pip`; `cibuildwheel` makes sure the right version of Python and pip will be executed. `{project}` can be used as a placeholder for the absolute path to the project's root.

Example: `pip install .`\
Example: `pip install pybind11`\
Example: `yum install -y libffi-dev && pip install .`

Platform-specific variants also available:\
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX`

### CIBW_MANYLINUX_X86_64_IMAGE, CIBW_MANYLINUX_I686_IMAGE {: #manylinux-image}
> Specify alternative manylinux docker images 

An alternative Docker image to be used for building [`manylinux`](https://github.com/pypa/manylinux) wheels. `cibuildwheel` will then pull these instead of the default images, [`quay.io/pypa/manylinux2010_x86_64`](https://quay.io/pypa/manylinux2010_x86_64) and [`quay.io/pypa/manylinux2010_i686`](https://quay.io/pypa/manylinux2010_i686).

The value of this option can either be set to `manylinux1` or `manylinux2010` to use the [official `manylinux` images](https://github.com/pypa/manylinux), or any other valid Docker image name.

Beware to specify a valid Docker image that can be used in the same way as the official, default Docker images: all necessary Python and pip versions need to be present in `/opt/python/`, and the `auditwheel` tool needs to be present for `cibuildwheel` to work. Apart from that, the architecture and relevant shared system libraries need to be manylinux1- or manylinux2010-compatible in order to produce valid `manylinux1`/`manylinux2010` wheels (see https://github.com/pypa/manylinux, [PEP 513](https://www.python.org/dev/peps/pep-0513/), and [PEP 571](https://www.python.org/dev/peps/pep-0571/) for more details).

Note that `auditwheel` detects the version of the `manylinux` standard in the Docker image through the `AUDITWHEEL_PLAT` environment variable, as `cibuildwheel` has no way of detecting the correct `--plat` command line argument to pass to `auditwheel` for a custom image. If a Docker image does not correctly set this `AUDITWHEEL_PLAT` environment variable, the `CIBW_ENVIRONMENT` option can be used to do so (e.g., `CIBW_ENVIRONMENT="manylinux2010_$(uname -m)"`).

Example: `manylinux1`\
Example: `dockcross/manylinux-x64`\
Example: `dockcross/manylinux-x86`

## Testing

### CIBW_TEST_COMMAND {: #test-command}
> Execute a shell command to test all built wheels

Shell command to run tests after the build. The wheel will be installed automatically and available for import from the tests. `{project}` can be used as a placeholder for the absolute path to the project's root and will be replaced by `cibuildwheel`.

On Linux and Mac, the command runs in a shell, so you can write things like `cmd1 && cmd2`. 

Example: `nosetests {project}/tests`

Platform-specific variants also available:
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX`

### CIBW_TEST_REQUIRES {: #test-requires}
> Install Python dependencies before running the tests

Space-separated list of dependencies required for running the tests.

Example: `pytest`\
Example: `nose==1.3.7 moto==0.4.31`

Platform-specific variants also available:
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX`

### CIBW_TEST_EXTRAS {: #test-extras}
> Install your wheel for testing using `extras_require`

Comma-separated list of
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
options that should be included when installing the wheel prior to running the
tests. This can be used to avoid having to redefine test dependencies in
`CIBW_TEST_REQUIRES` if they are already defined in `setup.py` or
`setup.cfg`.

Example: `test,qt` (will cause the wheel to be installed with `pip install <wheel_file>[test,qt]`)


Platform-specific variants also available:
`CIBW_TEST_EXTRAS_MACOS` | `CIBW_TEST_EXTRAS_WINDOWS` | `CIBW_TEST_EXTRAS_LINUX`

## Other

### CIBW_BUILD_VERBOSITY {: #test-extras}
> Increase/decrease the output of pip wheel

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
  .toctree-l3 {
    border-left: 10px solid transparent;
  }

  .options-toc {
    display: grid;
    grid-auto-columns: fit-content(20%) 1fr;
    grid-gap: 16px 32px;
    gap: 16px 32px;
    font-size: 90%;
    margin-bottom: 28px;
    margin-top: 28px;
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
        }).join(' ')

        markdown += '| '+namesMarkdown+' '
        markdown += '| '+option.description.trim()+' '
        markdown += '|\n'
      }
    }

    console.log('readme options markdown\n', markdown)
  });
</script>
