cibuildwheel
============

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

- Builds manylinux, macOS and Windows (32 and 64bit) wheels
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
      - pip install cibuildwheel
      - cibuildwheel --output-dir wheelhouse
    ```

  Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/).

- Create an `appveyor.yml` file in your repo.

    ```
    build_script:
      - pip install cibuildwheel
      - cibuildwheel --output-dir wheelhouse
    artifacts:
      - path: "wheelhouse\\*.whl"
        name: Wheels
    ```
    
  Appveyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [Appveyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info.
    
- Commit those files, enable building of your repo on Travis CI and Appveyor, and push.

All being well, you should get wheels delivered to you in a few minutes. 

> Got an error? Check the [checklist](#it-didnt-work) below.


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

| Environment variable: `CIBW_TEST_COMMAND`
| ---

Optional.

Shell command to run the tests. The project root should be included in the command as "{project}". The wheel will be installed automatically and available for import from the tests.

Example: `nosetests {project}/tests`

| Environment variable: `CIBW_TEST_REQUIRES`
| ---

Optional.

Space-separated list of dependencies required for running the tests.

Example: `pytest`  
Example: `nose==1.3.7 moto==0.4.31`

| Environment variable: `CIBW_SKIP` | 🔶 coming soon 🔶
| --- | ---

Optional.

Space-separated list of builds to skip. Each build has an identifier like `cp27-linux_x86_64` or `cp34-macosx_10_6_intel` - you can list ones to skip here and `cibuildwheel` won't try to build them.

The format is `python_tag-platform_tag`. The tags are as defined in [PEP 0425](https://www.python.org/dev/peps/pep-0425/#details).

Python tags look like `cp27` `cp34` `cp35` `cp36`

Platform tags look like `macosx_10_6_intel` `linux_x86_64` `linux_i386` `win32` `win_amd64`

You can also use shell-style globbing syntax (as per `fnmatch`) 

Example: `cp27-macosx_10_6_intel `  (don't build on Python 2 on Mac)  
Example: `cp27-win*`  (don't build on Python 2.7 on Windows)  
Example: `cp34-*`  (don't build on Python 3.4)  

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

It didn't work!
---------------

If your wheel didn't compile, check the list below for some debugging tips.

- A mistake in your config. To quickly test your config without doing a git push and waiting for your code, you can run the Linux build in a Docker container. Try `cibuildwheel --platform linux`.
- Missing dependency. You might need to install something inside on the build machine. You can do this in `.travis.yml` or `appveyor.yml`, with apt-get, brew or whatever Windows uses :P . Given how the Linux build works, we'll probably have to build something into `cibuildwheel`. Let's chat about that over in the issues!
- Windows: missing C feature. The Windows C compiler doesn't support C language features invented after 1990, so you'll have to backport your C code to C90. For me, this mostly involved putting my variable declarations at the top of the function like an animal.

Legal note
----------

Since `cibuildwheel` runs the wheel through delocate or auditwheel, it will automatically bundle library dependencies. This is similar to static linking - it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.


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

Credits
-------

`cibuildwheel` stands on the shoulders of giants. Massive props to-

- ⭐️ @matthew-brett for matthew-brett/multibuild and matthew-brett/delocate
- @PyPA for the manylinux Docker images pypa/manylinux
- @ogrisel for wheelhouse-uploader and `run_with_env.cmd`

See also
--------

If `cibuildwheel` is too limited for your needs, consider matthew-brett/multibuild. `multibuild` is a toolbox for building a wheel on various platforms. It can do a lot more than this project - it's used to build SciPy!
