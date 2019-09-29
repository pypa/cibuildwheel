cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel)

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Azure Pipelines, Travis CI, AppVeyor, and CircleCI - and it builds and tests your wheels across all of your platforms.

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

> \* Not supported on Azure Pipelines

- Builds manylinux, macOS and Windows (32 and 64bit) wheels using Azure Pipelines, Travis CI, AppVeyor, and CircleCI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works  **Travis CI** and **CircleCI** to build Linux and Mac wheels, and **AppVeyor** to build Windows wheels. **Azure Pipelines** supports all three.

|                 | Linux | macOS | Windows |
|-----------------|-------|-------|---------|
| Azure Pipelines | ✅    | ✅    | ✅      |
| Travis CI       | ✅    | ✅    |         |
| AppVeyor        |       |       | ✅      |
| CircleCI        | ✅    | ✅    |         |

`cibuildwheel` is not intended to run on your development machine. It will try to install packages globally; this is no good. Travis CI, CircleCI, and AppVeyor run their builds in isolated environments, so are ideal for this kind of script.


### Linux builds on Docker

Linux wheels are built in the [`manylinux1` docker images](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 513](https://www.python.org/dev/peps/pep-0513/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:
- Programs and libraries cannot be installed on the Travis CI Ubuntu host with `apt-get`, but can be installed inside of the Docker image using `yum` or manually. The same goes for environment variables that are potentially needed to customize the wheel building. `cibuildwheel` supports this by providing the `CIBW_ENVIRONMENT` and `CIBW_BEFORE_BUILD` options to setup the build environment inside the running Docker image. See [below](#options) for details on these options.
- The project directory is mounted in the running Docker instance as `/project`, the output directory for the wheels as `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that this is not available on CircleCI due to their Docker policies.
- Alternative dockers images can be specified with the `CIBW_MANYLINUX1_X86_64_IMAGE` and `CIBW_MANYLINUX1_I686_IMAGE` options to allow for a custom, preconfigured build environment for the Linux builds. See [below](#options) for more details.


Options
-------

```
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
- MacOS: calling cibuildwheel from a python3 script and getting a `ModuleNotFoundError`? Due to a [bug](https://bugs.python.org/issue22490) in CPython, you'll need to [unset the `__PYVENV_LAUNCHER__` variable](https://github.com/joerick/cibuildwheel/issues/133#issuecomment-478288597) before activating a venv.

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
- [TgCrypto](https://github.com/pyrogram/tgcrypto)
- [Twisted](https://github.com/twisted/twisted)

> Add repo here! Send a PR.

Legal note
----------

Since `cibuildwheel` runs the wheel through delocate or auditwheel, it might automatically bundle dynamically linked libraries from the build machine. 

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

### 0.12.0

_29 September 2019_

- ✨ Add CIBW_TEST_EXTRAS option, to allow testing using extra_require
  options. For example, set `CIBW_TEST_EXTRAS=test,qt` to make the wheel
  installed with `pip install <wheel_file>[test,qt]`
- 🛠 Update Python from 3.7.2 to 3.7.4 on macOS
- 🛠 Update OpenSSL patch to 1.0.2t on macOS

### 0.11.1

_28 May 2019_

- 🐛 Fix missing file in the release tarball, that was causing problems with
  Windows builds (#141)

### 0.11.0

_26 May 2019_

- ✨ Add support for building on Azure pipelines! This lets you build all
  Linux, Mac and Windows wheels on one service, so it promises to be the
  easiest to set up! Check out the quickstart in the docs, or 
  [cibuildwheel-azure-example](https://github.com/joerick/cibuildwheel-azure-example)
  for an example project. (#126, #132)
- 🛠 Internal change - the end-to-end test projects format was updated, so we
  can more precisely assert what should be produced for each one. (#136, #137).

### 0.10.2

_10 March 2019_

- 🛠 Revert temporary fix in macOS, that was working around a bug in pip 19 (#129)
- 🛠 Update Python to 2.7.16 on macOS
- 🛠 Update OpenSSL patch to 1.0.2r on macOS

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
- 🐛 Fixed a bug on AppVeyor where logs would appear in the wrong order due to output buffering (#24, thanks @YannickJadoul!)

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
