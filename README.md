cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel)

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Azure Pipelines, Travis CI, Appveyor, and CircleCI - and it builds and tests your wheels across all of your platforms.

**`cibuildwheel` is in beta**. It's brand new - I'd love for you to try it and help make it better!

What does it do?
----------------

|   | macOS 10.6+ | manylinux i686 | manylinux x86_64 |  Windows 32bit | Windows 64bit |
|---|---|---|---|---|---|
| Python 2.7 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.4 | ✅ | ✅ | ✅ | ✅* | ✅* |
| Python 3.5 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.6 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.7 | ✅ | ✅ | ✅ | ✅  | ✅  |

> * Not supported on Azure Pipelines

- Builds manylinux, macOS and Windows (32 and 64bit) wheels using Azure Pipelines, Travis CI, Appveyor, and CircleCI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works  **Travis CI** and **CircleCI** to build Linux and Mac wheels, and **Appveyor** to build Windows wheels. **Azure Pipelines** supports all three.

|                 | Linux | macOS | Windows |
|-----------------|-------|-------|---------|
| Azure Pipelines | ✅    | ✅    | ✅      |
| Travis CI       | ✅    | ✅    |         |
| Appveyor        |       |       | ✅      |
| CircleCI        | ✅    | ✅    |         |

`cibuildwheel` is not intended to run on your development machine. It will try to install packages globally; this is no good. Travis CI, CircleCI, and Appveyor run their builds in isolated environments, so are ideal for this kind of script.

### Minimal setup

<details>
    <summary><b>Azure Pipelines</b>
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/apple.svg" />
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/windows.svg" />
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/linux.svg" />
    </summary>

- Using Azure pipelines, you can build all three platforms on the same service. Create a `azure-pipelines.yml` file in your repo.

**azure-pipelines.yml**
```yaml
jobs:
- job: linux
  pool: {vmImage: 'Ubuntu-16.04'}
  steps: 
    - task: UsePythonVersion@0
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.10.1
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
- job: macos
  pool: {vmImage: 'macOS-10.13'}
  steps: 
    - task: UsePythonVersion@0
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.10.1
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
- job: windows
  pool: {vmImage: 'vs2017-win2016'}
  steps: 
    - {task: UsePythonVersion@0, inputs: {versionSpec: '2.7', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '2.7', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.5', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.5', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.6', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.6', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.7', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.7', architecture: x64}}
    - script: choco install vcpython27 -f -y
      displayName: Install Visual C++ for Python 2.7
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.10.1
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
```

</details>

<details>
    <summary><b>Travis CI</b>
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/apple.svg" />
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/linux.svg" />
    </summary>

- To build Linux and Mac wheels on Travis CI, create a `.travis.yml` file in your repo.

    ```
    language: python
    
    matrix:
      include:
        - sudo: required
          services:
            - docker
          env: PIP=pip
        - os: osx
          language: generic
          env: PIP=pip2

    script:
      - $PIP install cibuildwheel==0.10.1
      - cibuildwheel --output-dir wheelhouse
    ```

  Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](#delivering-to-pypi) below.

</details>

<details>
    <summary><b>CircleCI</b>
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/apple.svg" />
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/linux.svg" />
    </summary>
    
- To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

  ```
  version: 2

  jobs:
    linux-wheels:
      working_directory: ~/linux-wheels
      docker:
        - image: circleci/python:3.6
      steps:
        - checkout
        - setup_remote_docker
        - run:
            name: Build the Linux wheels.
            command: |
              pip install --user cibuildwheel
              cibuildwheel --output-dir wheelhouse
        - store_artifacts:
            path: wheelhouse/

    osx-wheels:
      working_directory: ~/osx-wheels
      macos:
        xcode: "10.0.0"
      steps:
        - checkout
        - run:
            name: Build the OS X wheels.
            command: |
              pip install --user cibuildwheel
              cibuildwheel --output-dir wheelhouse
        - store_artifacts:
            path: wheelhouse/

  workflows:
    version: 2
    all-tests:
      jobs:
        - linux-wheels
        - osx-wheels
  ```

  Note: CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

  CircleCI will store the built wheels for you - you can access them from the project console.

</details>


<details>
    <summary><b>Appveyor</b>
        <img width="16" src="https://unpkg.com/simple-icons@latest/icons/windows.svg" />
    </summary>

- To build Windows wheels on Appveyor, create an `appveyor.yml` file in your repo.

    ```
    build_script:
      - pip install cibuildwheel==0.10.1
      - cibuildwheel --output-dir wheelhouse
    artifacts:
      - path: "wheelhouse\\*.whl"
        name: Wheels
    ```
    
  Appveyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [Appveyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](#delivering-to-pypi) below.
    
</details>

- Commit those files, enable building of your repo on Travis CI and Appveyor, and push.

All being well, you should get wheels delivered to you in a few minutes. 

> ⚠️ Got an error? Check the [checklist](#it-didnt-work) below.

### Configuration overview

`cibuildwheel` allows for easy customization of the various phases of the build process demonstrated above:

|   | Option |   |
|---|---|---|
| **Target wheels** | `CIBW_PLATFORM` | Override the auto-detected target platform |
|   | `CIBW_BUILD` | Build only certain Python versions |
|   | `CIBW_SKIP` | Skip certain Python versions |
| **Build parameters** | `CIBW_BUILD_VERBOSITY` | Increase or decrease the output of `pip wheel` |
| **Build environment** | `CIBW_ENVIRONMENT` | Set environment variables needed during the build |
|   | `CIBW_BEFORE_BUILD` | Execute a shell command preparing each wheel's build |
|   | `CIBW_MANYLINUX1_X86_64_IMAGE` | Specify an alternative manylinx1 x86_64 docker image |
|   | `CIBW_MANYLINUX1_I686_IMAGE` | Specify an alternative manylinux1 i686 docker image |
| **Tests** | `CIBW_TEST_COMMAND` | Execute a shell command to test all built wheels |
|   | `CIBW_TEST_REQUIRES` | Install Python dependencies before running the tests |

A more detailed description of the options, the allowed values, and some examples can be found in the [Options](#options) section.

### Linux builds on Docker

Linux wheels are built in the [`manylinux1` docker images](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 513](https://www.python.org/dev/peps/pep-0513/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:
- Programs and libraries cannot be installed on the Travis CI Ubuntu host with `apt-get`, but can be installed inside of the Docker image using `yum` or manually. The same goes for environment variables that are potentially needed to customize the wheel building. `cibuildwheel` supports this by providing the `CIBW_ENVIRONMENT` and `CIBW_BEFORE_BUILD` options to setup the build environment inside the running Docker image. See [below](#options) for details on these options.
- The project directory is mounted in the running Docker instance as `/project`, the output directory for the wheels as `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that this is not available on CircleCI due to their Docker policies.
- Alternative dockers images can be specified with the `CIBW_MANYLINUX1_X86_64_IMAGE` and `CIBW_MANYLINUX1_I686_IMAGE` options to allow for a custom, preconfigured build environment for the Linux builds. See [below](#options) for more details.


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

Most of the config is via environment variables. These go into `.travis.yml`, `appveyor.yml`, and `.circleci/config.yml` nicely.

***

| Environment variable: `CIBW_PLATFORM` | Command line argument: `--platform`
| --- | ---

Options: `auto` `linux` `macos` `windows`

Default: `auto`

`auto` will auto-detect platform using environment variables, such as `TRAVIS_OS_NAME`/`APPVEYOR`/`CIRCLECI`.

For `linux` you need Docker running, on Mac or Linux. For `macos`, you need a Mac machine, and note that this script is going to automatically install MacPython on your system, so don't run on your development machine. For `windows`, you need to run in Windows, and it will build and test for all versions of Python at `C:\PythonXX[-x64]`.

***

| Environment variables: `CIBW_BUILD` and `CIBW_SKIP`
| ---

Optional.

Space-separated list of builds to build and skip. Each build has an identifier like `cp27-manylinux1_x86_64` or `cp34-macosx_10_6_intel` - you can list specific ones to build and `cibuildwheel` will only build those, and/or list ones to skip and `cibuildwheel` won't try to build them.

When both options are specified, both conditions are applied and only builds with a tag that matches `CIBW_BUILD` and does not match `CIBW_SKIP` will be built.

The format is `python_tag-platform_tag`. The tags are as defined in [PEP 0425](https://www.python.org/dev/peps/pep-0425/#details).

Python tags look like `cp27` `cp34` `cp35` `cp36` `cp37`

Platform tags look like `macosx_10_6_intel` `manylinux1_x86_64` `manylinux1_i686` `win32` `win_amd64`

You can also use shell-style globbing syntax (as per `fnmatch`) 

Examples:
- Only build on Python 3.6: `CIBW_BUILD`:`cp36-*`
- Skip building on Python 2.7 on the Mac: `CIBW_SKIP`:`cp27-macosx_10_6_intel`
- Skip building on Python 2.7 on all platforms: `CIBW_SKIP`:`cp27-*`
- Skip Python 2.7 on Windows: `CIBW_SKIP`:`cp27-win*`
- Skip Python 2.7 on 32-bit Windows: `CIBW_SKIP`:`cp27-win32`
- Skip Python 3.4 and Python 3.5: `CIBW_SKIP`:`cp34-* cp35-*`
- Skip Python 3.6 on Linux: `CIBW_SKIP`:`cp36-manylinux*`
- Only build on Python 3 and skip 32-bit builds: `CIBW_BUILD`:`cp3?-*` and `CIBW_SKIP`:`*-win32 *-manylinux1_i686`

**

| Environment variable: `CIBW_BUILD_VERBOSITY`
| ---

Optional.

An number from 1 to 3 to increase the level of verbosity (corresponding to invoking pip with `-v`, `-vv`, and `-vvv`), between -1 and -3 (`-q`, `-qq`, and `-qqq`), or just 0 (default verbosity). These flags are useful while debugging a build when the output of the actual build invoked by `pip wheel` is required.

Platform-specific variants also available:
`CIBW_BUILD_VERBOSITY_MACOS` | `CIBW_BUILD_VERBOSITY_WINDOWS` | `CIBW_BUILD_VERBOSITY_LINUX`

***

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

***

| Environment variable: `CIBW_BEFORE_BUILD`
| ---

Optional.

A shell command to run before building the wheel. This option allows you to run a command in **each** Python environment before the `pip wheel` command. This is useful if you need to set up some dependency so it's available during the build.

If dependencies are required to build your wheel (for example if you include a header from a Python module), set this to `pip install .`, and the dependencies will be installed automatically by pip. However, this means your package will be built twice - if your package takes a long time to build, you might wish to manually list the dependencies here instead.

The active Python binary can be accessed using `python`, and pip with `pip`; `cibuildwheel` makes sure the right version of Python and pip will be executed. `{project}` can be used as a placeholder for the absolute path to the project's root.

Example: `pip install .`  
Example: `pip install pybind11`  
Example: `yum install -y libffi-dev && pip install .`

Platform-specific variants also available:  
 `CIBW_BEFORE_BUILD_MACOS` | `CIBW_BEFORE_BUILD_WINDOWS` | `CIBW_BEFORE_BUILD_LINUX`

***

| Environment variables: `CIBW_MANYLINUX1_X86_64_IMAGE` and `CIBW_MANYLINUX1_I686_IMAGE`
| ---

Optional.

An alternative docker image to be used for building [`manylinux1`](https://github.com/pypa/manylinux) wheels. `cibuildwheel` will then pull these instead of the official images, [`quay.io/pypa/manylinux1_x86_64`](https://quay.io/pypa/manylinux1_i686) and [`quay.io/pypa/manylinux1_i686`](https://quay.io/pypa/manylinux1_i686).

Beware to specify a valid docker image that can be used the same as the official, default docker images: all necessary Python and pip versions need to be present in `/opt/python/`, and the `auditwheel` tool needs to be present for `cibuildwheel` to work. Apart from that, the architecture and relevant shared system libraries need to be manylinux1-compatible in order to produce valid `manylinux1` wheels (see https://github.com/pypa/manylinux and [PEP 513](https://www.python.org/dev/peps/pep-0513/) for more details).

Example: `dockcross/manylinux-x64`  
Example: `dockcross/manylinux-x86`

***

| Environment variable: `CIBW_TEST_COMMAND`
| ---

Optional.

Shell command to run tests after the build. The wheel will be installed automatically and available for import from the tests. `{project}` can be used as a placeholder for the absolute path to the project's root and will be replaced by `cibuildwheel`.

On Linux and Mac, the command runs in a shell, so you can write things like `cmd1 && cmd2`. 

Example: `nosetests {project}/tests`

Platform-specific variants also available:
`CIBW_TEST_COMMAND_MACOS` | `CIBW_TEST_COMMAND_WINDOWS` | `CIBW_TEST_COMMAND_LINUX`

***

| Environment variable: `CIBW_TEST_REQUIRES`
| ---

Optional.

Space-separated list of dependencies required for running the tests.

Example: `pytest`  
Example: `nose==1.3.7 moto==0.4.31`

Platform-specific variants also available:
`CIBW_TEST_REQUIRES_MACOS` | `CIBW_TEST_REQUIRES_WINDOWS` | `CIBW_TEST_REQUIRES_LINUX`


### Example YML syntax

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
- Missing dependency. You might need to install something on the build machine. You can do this in `.travis.yml`, `appveyor.yml`, or `.circleci/config.yml`, with apt-get, brew or whatever Windows uses :P . Given how the Linux build works, we'll probably have to build something into `cibuildwheel`. Let's chat about that over in the issues!
- Windows: missing C feature. The Windows C compiler doesn't support C language features invented after 1990, so you'll have to backport your C code to C90. For me, this mostly involved putting my variable declarations at the top of the function like an animal.

Working examples
----------------

Here are some repos that use cibuildwheel. 

- [pyinstrument_cext](https://github.com/joerick/pyinstrument_cext)
- [websockets](https://github.com/aaugustin/websockets)
- [Parselmouth](https://github.com/YannickJadoul/Parselmouth)
- [python-admesh](https://github.com/admesh/python-admesh)
- [pybase64](https://github.com/mayeut/pybase64)
- [KDEpy](https://github.com/tommyod/KDEpy)
- [AutoPy](https://github.com/autopilot-rs/autopy)
- [apriltags2-ethz](https://github.com/safijari/apriltags2_ethz)

> Add repo here! Send a PR.

Legal note
----------

Since `cibuildwheel` runs the wheel through delocate or auditwheel, it might automatically bundle dynamically linked libraries from the build machine. 

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

### 0.10.1

_3 February 2019_

- 🐛 Fix build stalling on macOS (that was introduced in pip 19) (#122)
- 🐛 Fix "AttributeError: 'Popen' object has no attribute 'args'" on Python 2.7 for Linux builds (#108)
- 🛠 Update Python from 3.6.7, 3.7.1 to 3.6.8, 3.7.2 on macOS
- 🛠 Update openssl patch from 1.0.2p to 1.0.2q on macOS
- 🛠 Sorting build options dict items when printing preamble (#114)

### 0.10.0

_23 September 2018_

- ✨ Add `CIBW_BUILD` option, for specifying which specific builds to perform (#101)
- ✨ Add support for building Mac and Linux on CircleCI (#91, #97)
- 🛠 Improved support for building universal wheels (#95)
- 🛠 Ensure log output is unbuffered and therefore in the correct order (#92)
- 🛠 Improved error reporting for errors that occur inside a package's setup.py (#88)
- ⚠️ Removed support for Python 3.3 on Windows.

### 0.9.4

_29 July 2018_

- 🛠 CIBW_TEST_COMMAND now runs in a shell on Mac (as well as Linux) (#81)

### 0.9.3

_10 July 2018_

- 🛠 Update to Python 3.6.6 on macOS (#82)
- ✨ Add support for building Python 3.7 wheels on Windows (#76)
- ⚠️ Deprecated support for Python 3.3 on Windows.

### 0.9.2

_1 July 2018_

- 🛠  Update Python 3.7.0rc1 to 3.7.0 on macOS (#79)

### 0.9.1

_18 June 2018_

- 🛠 Removed the need to use `{python}` and `{pip}` in `CIBW_BEFORE_BUILD` statements, by ensuring the correct version is always on the path at `python` and `pip` instead. (#60)
- 🛠 We now patch the _ssl module on Python 3.4 and 3.5 so these versions can still make SSL web requests using TLS 1.2 while building. (#71)

### 0.9.0

_18 June 2018_

- ✨ Add support for Python 3.7 (#73)

### 0.8.0

_4 May 2018_

- ⚠️ Drop support for Python 3.3 on Linux (#67)
- 🐛 Fix TLS by updating setuptools (#69)

### 0.7.1

_2 April 2017_

- 🐛 macOS: Fix Pip bugs resulting from PyPI TLS 1.2 enforcement
- 🐛 macOS: Fix brew Python3 version problems in the CI

### 0.7.0

_7 January 2018_

- ✨ You can now specify a custom docker image using the `CIBW_MANYLINUX1_X86_64_IMAGE` and `CIBW_MANYLINUX1_I686_IMAGE` options. (#46)
- 🐛 Fixed a bug where cibuildwheel would download and build a package from PyPI(!) instead of building the package on the local machine. (#51)

### 0.6.0

_9 October 2017_

- ✨ On the Linux build, the host filesystem is now accessible via `/host` (#36)
- 🐛 Fixed a bug where setup.py scripts would run the wrong version of Python when running subprocesses on Linux (#35)

### 0.5.1

_10 September 2017_

- 🐛 Fixed a couple of bugs on Python 3.
- ✨ Added experimental support for Mac builds on [Bitrise.io](https://www.bitrise.io)

### 0.5.0

_7 September 2017_

- ✨ `CIBW_ENVIRONMENT` added. You can now set environment variables for each build, even within the Docker container on Linux. This is a big one! (#21)
- ✨ `CIBW_BEFORE_BUILD` now runs in a system shell on all platforms. You can now do things like `CIBW_BEFORE_BUILD="cmd1 && cmd2"`. (#32)

### 0.4.1

_14 August 2017_

- 🐛 Fixed a bug on Windows where subprocess' output was hidden (#23)
- 🐛 Fixed a bug on Appveyor where logs would appear in the wrong order due to output buffering (#24, thanks @YannickJadoul!)

### 0.4.0

_23 July 2017_

- 🐛 Fixed a bug that was increasing the build time by building the wheel twice. This was a problem for large projects that have a long build time. If you're upgrading and you need the old behaviour, use `CIBW_BEFORE_BUILD={pip} install .`, or install exactly the dependencies you need in `CIBW_BEFORE_BUILD`. See #18.

### 0.3.0

_27 June 2017_

- ⚠️ Removed Python 2.6 support on Linux (#12)

### 0.2.1

_11 June 2017_

- 🛠 Changed the build process to install the package before building the wheel - this allows direct dependencies to be installed first (#9, thanks @tgarc!)
- ✨ Added Python 3 support for the main process, for systems where Python 3 is the default (#8, thanks @tgarc).

### 0.2.0

_13 April 2017_

- ✨ Added `CIBW_SKIP` option, letting users explicitly skip a build 
- ✨ Added `CIBW_BEFORE_BUILD` option, letting users run a shell command before the build starts

### 0.1.3

_31 March 2017_

- 🌟 First public release!

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
- Matthieu Darbois [@mayeut](https://github.com/mayeut)

Credits
-------

`cibuildwheel` stands on the shoulders of giants. 

- ⭐️ @matthew-brett for [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild) and [matthew-brett/delocate](http://github.com/matthew-brett/delocate)
- @PyPA for the manylinux Docker images [pypa/manylinux](https://github.com/pypa/manylinux)
- @ogrisel for [wheelhouse-uploader](https://github.com/ogrisel/wheelhouse-uploader) and `run_with_env.cmd`

Massive props also to-

- @zfrenchee for [help debugging many issues](https://github.com/joerick/cibuildwheel/issues/2)
- @lelit for some great bug reports and [contributions](https://github.com/joerick/cibuildwheel/pull/73)
- @mayeut for a [phenomenal PR](https://github.com/joerick/cibuildwheel/pull/71) patching Python itself for better compatibility!

See also
--------

If you'd like to keep wheel building separate from the package itself, check out [astrofrog/autowheel](https://github.com/astrofrog/autowheel). It builds packages using cibuildwheel from source distributions on PyPI.

If `cibuildwheel` is too limited for your needs, consider [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a toolbox for building a wheel on various platforms. It can do a lot more than this project - it's used to build SciPy!
