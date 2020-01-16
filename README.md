cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.readthedocs.io/en/stable/?badge=stable) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel) [![Build Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/joerick.cibuildwheel?branchName=master)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=2&branchName=master)

[Documentation](https://cibuildwheel.readthedocs.org)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Azure Pipelines, Travis CI, AppVeyor, and CircleCI - and it builds and tests your wheels across all of your platforms.


What does it do?
----------------

|   | macOS x86_64 | Windows 64bit | Windows 32bit | manylinux x86_64 | manylinux i686 | manylinux aarch64 | manylinux ppc64le | manylinux s390x |
|---|---|---|---|---|---|---|---|---|
| CPython 2.7     | ✅ | ✅¹ | ✅¹ | ✅ | ✅ |     |     |     |
| CPython 3.5     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅  | ✅  | ✅  |
| CPython 3.6     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅  | ✅  | ✅  |
| CPython 3.7     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅  | ✅  | ✅  |
| CPython 3.8     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅  | ✅  | ✅  |
| PyPy 2.7 v7.3.0 | ✅ |     | ✅  | ✅ |    |     |     |     |
| PyPy 3.6 v7.3.0 | ✅ |     | ✅  | ✅ |    |     |     |     |

<sup>¹ Not supported on Travis</sup>

- Builds manylinux, macOS and Windows wheels for CPython and PyPy using Azure Pipelines, Travis CI, AppVeyor, and CircleCI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works on **Travis CI** and **Azure Pipelines** to build wheels for all three supported platforms (Linux, macOS, Windows). On **CircleCI** Linux and macOS wheels can be built, and on **AppVeyor** Linux and Windows are supported.

|                 | Linux | macOS | Windows |
|-----------------|-------|-------|---------|
| Azure Pipelines | ✅    | ✅    | ✅      |
| Travis CI       | ✅    | ✅    | ✅      |
| AppVeyor        | ✅    |       | ✅      |
| CircleCI        | ✅    | ✅    |         |

`cibuildwheel` is not intended to run on your development machine. Because it uses system Python from Python.org it will try to install packages globally - not what you expect from a build tool! Instead, isolated CI services like Travis CI, CircleCI, Azure Pipelines and AppVeyor are ideal.

<!--intro-end-->

Example setup
-------------

To build manylinux, macOS, and Windows wheels on Travis CI and upload them to PyPI whenever you tag a version, you could use this `.travis.yml`:

```yaml
language: python

jobs:
  include:
    # perform a linux build
    - services: docker
    # and a mac build
    - os: osx
      language: shell
    # and a windows build
    - os: windows
      language: shell
      before_install:
        - choco install python --version 3.8.0
        - export PATH="/c/Python38:/c/Python38/Scripts:$PATH"

env:
  global:
    - TWINE_USERNAME=__token__
    # Note: TWINE_PASSWORD is set to a PyPI API token in Travis settings

install:
  - python3 -m pip install cibuildwheel==1.1.0

script:
  # build the wheels, put them into './wheelhouse'
  - python3 -m cibuildwheel --output-dir wheelhouse

after_success:
  # if the release was tagged, upload them to PyPI
  - |
    if [[ $TRAVIS_TAG ]]; then
      python3 -m pip install twine
      python3 -m twine upload wheelhouse/*.whl
    fi
```

For more information, including how to build on Appveyor, Azure, CircleCI, check out the [documentation](https://cibuildwheel.readthedocs.org) and also check out [the examples](https://github.com/joerick/cibuildwheel/tree/master/examples).

Options
-------

|   | Option | Description |
|---|--------|-------------|
| **Build selection** | [`CIBW_PLATFORM`](https://cibuildwheel.readthedocs.io/en/stable/options/#platform)  | Override the auto-detected target platform |
|   | [`CIBW_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  [`CIBW_SKIP`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  | Choose the Python versions to build |
| **Build environment** | [`CIBW_ENVIRONMENT`](https://cibuildwheel.readthedocs.io/en/stable/options/#environment)  | Set environment variables needed during the build |
|   | [`CIBW_BEFORE_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-build)  | Execute a shell command preparing each wheel's build |
|   | [`CIBW_REPAIR_WHEEL_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#repair-wheel-command)  | Execute a shell command to repair each (non-pure Python) built wheel |
|   | [`CIBW_MANYLINUX_X86_64_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  [`CIBW_MANYLINUX_I686_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  [`CIBW_MANYLINUX_PYPY_X86_64_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  | Specify alternative manylinux docker images |
| **Testing** | [`CIBW_TEST_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-command)  | Execute a shell command to test each built wheel |
|   | [`CIBW_BEFORE_TEST`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-test)  | Execute shell command to prepare test environment |
|   | [`CIBW_TEST_REQUIRES`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-requires)  | Install Python dependencies before running the tests |
|   | [`CIBW_TEST_EXTRAS`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-extras)  | Install your wheel for testing using extras_require |
| **Other** | [`CIBW_BUILD_VERBOSITY`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-extras)  | Increase/decrease the output of pip wheel |

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

> Add your repo here! Send a PR.

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

### 1.1.0

_7 December 2019_

- ✨ Add support for building manylinux2014 wheels. To use, set
  `CIBW_MANYLINUX_X86_64_IMAGE` and CIBW_MANYLINUX_I686_IMAGE to
  `manylinux2014`.
- ✨ Add support for [Linux on Appveyor](https://www.appveyor.com/blog/2018/03/06/appveyor-for-linux/) (#204, #207)
- ✨ Add `CIBW_REPAIR_WHEEL_COMMAND` env variable, for changing how
  `auditwheel` or `delocate` are invoked, or testing an equivalent on
  Windows. (#211)
- 📚 Added some travis example configs - these are available in /examples. (#228)

### 1.0.0

_10 November 2019_

- ✨ Add support for building Python 3.8 wheels! (#180)
- ✨ Add support for building manylinux2010 wheels. cibuildwheel will now
  build using the manylinux2010 images by default. If your project is still
  manylinux1 compatible, you should get both manylinux1 and manylinux2010
  wheels - you can upload both to PyPI. If you always require manylinux1 wheels, you can
  build using the old manylinux1 image using the [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image) option.
  (#155)
- 📚 Documentation is now on its [own mini-site](https://cibuildwheel.readthedocs.io),
   rather than on the README (#169)
- ✨ Add support for building Windows wheels on Travis CI. (#160)
- 🛠 If you set `CIBW_TEST_COMMAND`, your tests now run in a virtualenv. (#164)
- 🛠 Windows now uses Python as installed by nuget, rather than the versions
  installed by the various CI providers. (#180)
- 🛠 Update Python from 2.7.16 to 2.7.17 and 3.7.4 to 3.7.5 on macOS (#171)
- ⚠️ Removed support for Python 3.4 (#168)

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

For more info on how to contribute to cibuildwheel, see the [docs](https://cibuildwheel.readthedocs.io/en/latest/contributing/).

Maintainers
-----------

- Joe Rickerby [@joerick](https://github.com/joerick)
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
========

If you'd like to keep wheel building separate from the package itself, check out [astrofrog/autowheel](https://github.com/astrofrog/autowheel). It builds packages using cibuildwheel from source distributions on PyPI.

If `cibuildwheel` is too limited for your needs, consider [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a toolbox for building a wheel on various platforms. It can do a lot more than this project - it's used to build SciPy!
