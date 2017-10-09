cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master)

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Travis CI and Appveyor - and it builds and tests your wheels across all of your platforms.

**`cibuildwheel` is in beta**. It's brand new - I'd love for you to try it and help make it better!

What does it do?
----------------

|   | macOS 10.6+ | manylinux i686 | manylinux x86_64 |  Windows 32bit | Windows 64bit |
|---|---|---|---|---|---|
| Python 2.7 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python 3.3 |    | ✅ | ✅ | ✅ | ✅ |
| Python 3.4 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python 3.5 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python 3.6 | ✅ | ✅ | ✅ | ✅ | ✅ |

- Builds manylinux, macOS and Windows (32 and 64bit) wheels using Travis CI and Appveyor
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works on **Travis CI** to build Linux and Mac wheels, and **Appveyor** to build Windows wheels.

`cibuildwheel` is not intended to run on your development machine. It will try to install packages globally; this is no good. Travis CI and Appveyor run their builds in isolated environments, so are ideal for this kind of script.

### Minimal setup

- Create a `.travis.yml` file in your repo.

    ```
    matrix:
      include:
        - sudo: required
          services:
            - docker
        - os: osx

    script:
      - pip install cibuildwheel==0.6.0
      - cibuildwheel --output-dir wheelhouse
    ```

  Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](#delivering-to-pypi) below.

- Create an `appveyor.yml` file in your repo.

    ```
    build_script:
      - pip install cibuildwheel==0.6.0
      - cibuildwheel --output-dir wheelhouse
    artifacts:
      - path: "wheelhouse\\*.whl"
        name: Wheels
    ```
    
  Appveyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [Appveyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](#delivering-to-pypi) below.
    
- Commit those files, enable building of your repo on Travis CI and Appveyor, and push.

All being well, you should get wheels delivered to you in a few minutes. 

> ⚠️ Got an error? Check the [checklist](#it-didnt-work) below.

### Configuration overview

`cibuildwheel` allows for easy customization of the various phases of the build process demonstrated above:

|   | Option |   |
|---|---|---|
| **Target wheels** | `CIBW_PLATFORM` | Override the auto-detected target platform |
|   | `CIBW_SKIP` | Skip certain Python versions |
| **Build environment** | `CIBW_ENVIRONMENT` | Set environment variables needed during the build |
|   | `CIBW_BEFORE_BUILD` | Execute a shell command preparing each wheel's build |
| **Tests** | `CIBW_TEST_COMMAND` | Execute a shell command to test all built wheels |
|   | `CIBW_TEST_REQUIRES` | Install Python dependencies before running the tests |

A more detailed description of the options, the allowed values, and some examples can be found in the [Options](#options) section.

### Linux builds on Docker

Linux wheels are built in the [`manylinux1` docker images](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 513](https://www.python.org/dev/peps/pep-0513/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:
- Progams and libraries cannot be installed on the Travis CI Ubuntu host with `apt-get`, but can be installed inside of the Docker image using `yum` or manually. The same goes for environment variables that are potentially needed to customize the wheel building. `cibuildwheel` supports this by providing the `CIBW_ENVIRONMENT` and `CIBW_BEFORE_BUILD` options to setup the build environment inside the running Docker image. See [below](#options) for details on these options.
- The project directory is mounted in the running Docker instance as `/project`, the output directory for the wheels as `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.


Options
-------

```
usage: cibuildwheel [-h]
                    [--output-dir OUTPUT_DIR]
                    [--platform PLATFORM]
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

```

Most of the config is via environment variables. These go into `.travis.yml` and `appveyor.yml` nicely.

| Environment variable: `CIBW_PLATFORM` | Command line argument: `--platform`
| --- | ---

Options: `auto` `linux` `macos` `windows`

Default: `auto`

`auto` will auto-detect platform using environment variables, such as `TRAVIS_OS_NAME`/`APPVEYOR`.

For `linux` you need Docker running, on Mac or Linux. For `macos`, you need a Mac machine, and note that this script is going to automatically install MacPython on your system, so don't run on your development machine. For `windows`, you need to run in Windows, and it will build and test for all versions of Python at `C:\PythonXX[-x64]`.

| Environment variable: `CIBW_SKIP`
| ---

Optional.

Space-separated list of builds to skip. Each build has an identifier like `cp27-manylinux1_x86_64` or `cp34-macosx_10_6_intel` - you can list ones to skip here and `cibuildwheel` won't try to build them.

The format is `python_tag-platform_tag`. The tags are as defined in [PEP 0425](https://www.python.org/dev/peps/pep-0425/#details).

Python tags look like `cp27` `cp34` `cp35` `cp36`

Platform tags look like `macosx_10_6_intel` `manylinux1_x86_64` `manylinux1_i686` `win32` `win_amd64`

You can also use shell-style globbing syntax (as per `fnmatch`) 

Example: `cp27-macosx_10_6_intel`  (don't build on Python 2 on Mac)  
Example: `cp27-win*`  (don't build on Python 2.7 on Windows)  
Example: `cp34-* cp35-*`  (don't build on Python 3.4 or Python 3.5)  

| Environment variable: `CIBW_ENVIRONMENT`
| ---

Optional.

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

| Environment variable: `CIBW_BEFORE_BUILD`
| ---

Optional.

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), set this to `{pip} install .`, and the dependencies will be installed automatically by pip. However, this means your package will be built twice - if your package takes a long time to build, you might wish to manually list the dependencies here instead.

The active Python binary can be accessed using `{python}`, and pip with `{pip}`. These are useful when you need to write `python3` or `pip3` on a Python 3.x build.

Example: `{pip} install .`  
Example: `{pip} install pybind11`  
Example: `yum install -y libffi-dev && {pip} install .`

Platform-specific variants also available:  
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX`

| Environment variable: `CIBW_TEST_COMMAND`
| ---

Optional.

Shell command to run tests after the build. The wheel will be installed automatically and available for import from the tests. The project root should be included in the command as "{project}".

Example: `nosetests {project}/tests`

| Environment variable: `CIBW_TEST_REQUIRES`
| ---

Optional.

Space-separated list of dependencies required for running the tests.

Example: `pytest`  
Example: `nose==1.3.7 moto==0.4.31`

--

#### Example YML syntax

<table>
<tr><td><i>example .travis.yml environment variables</i><pre><code>env:
  global:
    - CIBW_TEST_REQUIRES=nose
    - CIBW_TEST_COMMAND="nosetests {project}/tests"
</code></pre></td>
<td><i>example appveyor.yml environment variables</i><pre><code>environment:
  global:
    CIBW_TEST_REQUIRES: nose
    CIBW_TEST_COMMAND: "nosetests {project}\\tests"
</code></pre></td>
</tr></table>

Delivering to PyPI
------------------

After you've built your wheels, you'll probably want to deliver them to PyPI.

### Manual method

On your development machine, do the following...

```bash
# Clear out your 'dist' folder. 
rm -rf dist
# Make a source distribution
python setup.py sdist

# 🏃🏻
# Go and download your wheel files from wherever you put them. Put 
# them all into the 'dist' folder.

# Upload using 'twine' (you may need to 'pip install twine')
twine upload dist/*
```

### Semi-automatic method using wheelhouse-uploader

Obviously, manual steps are for chumps, so we can automate this a little by using [wheelhouse-uploader](https://github.com/ogrisel/wheelhouse-uploader).

> Quick note from me - using S3 as a storage didn't work due to a [bug](https://issues.apache.org/jira/browse/LIBCLOUD-792) in libcloud. Feel free to use my fork of that package that fixes the bug `pip install https://github.com/joerick/libcloud/archive/v1.5.0-s3fix.zip`

### Automatic method

If you don't need much control over the release of a package, you can set up cibuildwheel to deliver the wheels straight to PyPI. This doesn't require any cloud storage to work - you just need to bump the version and tag it.

Check out [this example repo](https://github.com/joerick/cibuildwheel-autopypi-example) for instructions on how to set this up.

It didn't work!
---------------

If your wheel didn't compile, check the list below for some debugging tips.

- A mistake in your config. To quickly test your config without doing a git push and waiting for your code to build on CI, you can run the Linux build in a Docker container. On Mac or Linux, with Docker running, try `cibuildwheel --platform linux`. You'll have to bring your config into the current environment first.
- Missing dependency. You might need to install something on the build machine. You can do this in `.travis.yml` or `appveyor.yml`, with apt-get, brew or whatever Windows uses :P . Given how the Linux build works, we'll probably have to build something into `cibuildwheel`. Let's chat about that over in the issues!
- Windows: missing C feature. The Windows C compiler doesn't support C language features invented after 1990, so you'll have to backport your C code to C90. For me, this mostly involved putting my variable declarations at the top of the function like an animal.

Working examples
----------------

Here are some repos that use cibuildwheel. 

- [pyinstrument_cext](https://github.com/joerick/pyinstrument_cext)
- [websockets](https://github.com/aaugustin/websockets)
- [Parselmouth](https://github.com/YannickJadoul/Parselmouth)
- [python-admesh](https://github.com/admesh/python-admesh)

> Add repo here! Send a PR.

Legal note
----------

Since `cibuildwheel` runs the wheel through delocate or auditwheel, it will automatically bundle library dependencies. This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

### 0.5.1

- Fixed a couple of bugs on Python 3.
- Added experimental support for Mac builds on [Bitrise.io](https://www.bitrise.io)

### 0.5.0

- `CIBW_ENVIRONMENT` added. You can now set environment variables for each build, even within the Docker container on Linux. This is a big one! (#21)
- `CIBW_BEFORE_BUILD` now runs in a system shell on all platforms. You can now do things like `CIBW_BEFORE_BUILD="cmd1 && cmd2"`. (#32)

### 0.4.1

- Fixed a bug on Windows where subprocess' output was hidden (#23)
- Fixed a bug on Appveyor where logs would appear in the wrong order due to output buffering (#24, thanks @YannickJadoul!)

### 0.4.0

- Fixed a bug that was increasing the build time by building the wheel twice. This was a problem for large projects that have a long build time. If you're upgrading and you need the old behaviour, use `CIBW_BEFORE_BUILD={pip} install .`, or install exactly the dependencies you need in `CIBW_BEFORE_BUILD`. See #18.

### 0.3.0

- Removed Python 2.6 support on Linux (#12)

### 0.2.1

11 June 2017

- Changed the build process to install the package before building the wheel - this allows direct dependencies to be installed first (#9, thanks @tgarc!)
- Added Python 3 support for the main process, for systems where Python 3 is the default (#8, thanks @tgarc).

### 0.2.0

13 April 2017

- Added `CIBW_SKIP` option, letting users explicitly skip a build 
- Added `CIBW_BEFORE_BUILD` option, letting users run a shell command before the build starts

### 0.1.3

31 March 2017

- First public release!

Contributing
============

Wheel-building is pretty complex. I expect users to find many edge-cases - please help the rest of the community out by documenting these, adding features to support them, and reporting bugs.

I plan to be pretty liberal in accepting pull requests, as long as they align with the design goals below.

`cibuildwheel` is indie open source. I'm not paid to work on this.

Design Goals
------------

- `cibuildwheel` should wrap the complexity of wheel building.
- The user interface to `cibuildwheel` is the build script (e.g. `.travis.yml`). Feature additions should not increase the complexity of this script.
- Options should be environment variables (these lend themselves better to YML config files). They should be prefixed with `CIBW_`.
- Options should be generalise to all platforms. If platform-specific options are required, they should be namespaced e.g. `CIBW_TEST_COMMAND_MACOS`

Other notes:

- The platforms are very similar, until they're not. I'd rather have straight-forward code than totally DRY code, so let's keep airy platfrom abstractions to a minimum.
- I might want to break the options into a shared config file one day, so that config is more easily shared. That has motivated some of the design decisions.

Maintainers
-----------

- Joe Rickerby [@joerick](https://github.com/joerick)
- Tomas Garcia [@tgarc](https://github.com/tgarc)
- Yannick Jadoul [@YannickJadoul](https://github.com/YannickJadoul)

Credits
-------

`cibuildwheel` stands on the shoulders of giants. Massive props to-

- ⭐️ @matthew-brett for [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild) and [matthew-brett/delocate](http://github.com/matthew-brett/delocate)
- @PyPA for the manylinux Docker images [pypa/manylinux](https://github.com/pypa/manylinux)
- @ogrisel for [wheelhouse-uploader](https://github.com/ogrisel/wheelhouse-uploader) and `run_with_env.cmd`
- @zfrenchee for [help debugging many issues](https://github.com/joerick/cibuildwheel/issues/2)

See also
--------

If `cibuildwheel` is too limited for your needs, consider [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a toolbox for building a wheel on various platforms. It can do a lot more than this project - it's used to build SciPy!
