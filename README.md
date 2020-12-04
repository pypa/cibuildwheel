cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.readthedocs.io/en/stable/?badge=stable) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel) [![Build Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/joerick.cibuildwheel?branchName=master)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=2&branchName=master)

[Documentation](https://cibuildwheel.readthedocs.org)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Azure Pipelines, Travis CI, AppVeyor, GitHub Actions and CircleCI - and it builds and tests your wheels across all of your platforms.


What does it do?
----------------

|   | macOS x86_64 | Windows 64bit | Windows 32bit | manylinux x86_64 | manylinux i686 | manylinux aarch64 | manylinux ppc64le | manylinux s390x |
|---|---|---|---|---|---|---|---|---|
| CPython 2.7     | ✅ | ✅¹ | ✅¹ | ✅ | ✅ |    |    |    |
| CPython 3.5     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅² | ✅² | ✅³ |
| CPython 3.6     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅² | ✅² | ✅³ |
| CPython 3.7     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅² | ✅² | ✅³ |
| CPython 3.8     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅² | ✅² | ✅³ |
| CPython 3.9     | ✅ | ✅  | ✅  | ✅ | ✅ | ✅² | ✅² | ✅³ |
| PyPy 2.7 v7.3.3 | ✅ |    | ✅  | ✅ |    |    |    |    |
| PyPy 3.6 v7.3.3 | ✅ |    | ✅  | ✅ |    |    |    |    |
| PyPy 3.7 (beta) v7.3.3 | ✅ |    | ✅  | ✅ |    |    |    |    |

<sup>¹ Not supported on Travis</sup><br>
<sup>² Only supported on Travis</sup><br>
<sup>³ Beta support until Travis CI fixes <a href="https://travis-ci.community/t/no-space-left-on-device-for-system-z/5954/11">a bug</a></sup><br>

- Builds manylinux, macOS and Windows wheels for CPython and PyPy using Azure Pipelines, Travis CI, AppVeyor, and CircleCI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works on **Travis CI**, **Azure Pipelines**, **AppVeyor**, **GitHub Actions**, **CircleCI**, and **Gitlab CI**. Check the table below for supported platforms on each service:

|                 | Linux | macOS | Windows | Linux ARM |
|-----------------|-------|-------|---------|--------------|
| Azure Pipelines | ✅    | ✅    | ✅      | ✴️¹           |
| Travis CI       | ✅    | ✅    | ✅      | ✅           |
| AppVeyor        | ✅    | ✅    | ✅      |              |
| GitHub Actions  | ✅    | ✅    | ✅      | ✴️¹           |
| CircleCI        | ✅    | ✅    |         |              |
| Gitlab CI       | ✅    |       |         |              |

<sup>¹ Requires a "third-party build host"; expected to work with cibuildwheel but not directly tested by our CI.</sup><br>

`cibuildwheel` is not intended to run on your development machine. Because it uses system Python from Python.org it will try to install packages globally - not what you expect from a build tool! Instead, isolated CI services like those mentioned above are ideal.

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
        # make sure it's on PATH as 'python3'
        - ln -s /c/Python38/python.exe /c/Python38/python3.exe

env:
  global:
    - TWINE_USERNAME=__token__
    # Note: TWINE_PASSWORD is set to a PyPI API token in Travis settings

install:
  - python3 -m pip install cibuildwheel==1.7.1

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

For more information, including how to build on GitHub Actions, Appveyor, Azure Pipelines, or CircleCI, check out the [documentation](https://cibuildwheel.readthedocs.org) and the [examples](https://github.com/joerick/cibuildwheel/tree/master/examples).

Options
-------

<!-- START bin/project.py -->

| Name                    | Stars&nbsp; | CI | OS | Notes |
|-------------------------|-------|----|----|:------|
| [Matplotlib][]          | ![Matplotlib stars][] | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The venerable Matplotlib, a Python library with C++ portions |
| [twisted-iocpsupport][] | ![twisted-iocpsupport stars][] | ![github icon][] | ![windows icon][] | A submodule of Twisted that hooks into native C APIs using Cython. |
| [websockets][]          | ![websockets stars][] |  |  |  |
| [aiortc][]              | ![aiortc stars][] |  |  |  |
| [coverage.py][]         | ![coverage.py stars][] |  |  | The coverage tool for Python |
| [creme][]               | ![creme stars][] |  |  |  |
| [PyAV][]                | ![PyAV stars][] |  |  |  |
| [aioquic][]             | ![aioquic stars][] |  |  |  |
| [AutoPy][]              | ![AutoPy stars][] |  |  |  |
| [pikepdf][]             | ![pikepdf stars][] |  |  |  |
| [Parselmouth][]         | ![Parselmouth stars][] | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python interface to the Praat software package, using pybind11, C++17 and CMake, with the core Praat static library built only once and shared between wheels. |
| [KDEpy][]               | ![KDEpy stars][] |  |  |  |
| [bx-python][]           | ![bx-python stars][] | ![travisci icon][] | ![apple icon][] ![linux icon][] | A library that includes Cython extensions. |
| [pybase64][]            | ![pybase64 stars][] |  |  |  |
| [TgCrypto][]            | ![TgCrypto stars][] |  |  |  |
| [etebase-py][]          | ![etebase-py stars][] | ![travisci icon][] |  | Python bindings to a Rust library using `setuptools-rust`, and `sccache` for improved speed. |
| [gmic-py][]             | ![gmic-py stars][] |  |  |  |
| [fathon][]              | ![fathon stars][] |  |  |  |
| [pyinstrument_cext][]   | ![pyinstrument_cext stars][] | ![travisci icon][] ![appveyor icon][] |  | A simple C extension, without external dependencies |
| [python-admesh][]       | ![python-admesh stars][] |  |  |  |
| [xmlstarlet][]          | ![xmlstarlet stars][] | ![github icon][] |  | Python 3.6+ CFFI bindings with true MSVC build. |
| [apriltags2-ethz][]     | ![apriltags2-ethz stars][] |  |  |  |

[Matplotlib]: https://github.com/matplotlib/matplotlib
[Matplotlib stars]: https://img.shields.io/github/stars/matplotlib/matplotlib?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[twisted-iocpsupport]: https://github.com/twisted/twisted-iocpsupport
[twisted-iocpsupport stars]: https://img.shields.io/github/stars/twisted/twisted?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[websockets]: https://github.com/aaugustin/websockets
[websockets stars]: https://img.shields.io/github/stars/aaugustin/websockets?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[aiortc]: https://github.com/aiortc/aiortc
[aiortc stars]: https://img.shields.io/github/stars/aiortc/aiortc?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[coverage.py]: https://github.com/nedbat/coveragepy
[coverage.py stars]: https://img.shields.io/github/stars/nedbat/coveragepy?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[creme]: https://github.com/creme-ml/creme
[creme stars]: https://img.shields.io/github/stars/creme-ml/creme?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[PyAV]: https://github.com/PyAV-Org/PyAV
[PyAV stars]: https://img.shields.io/github/stars/PyAV-Org/PyAV?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[aioquic]: https://github.com/aiortc/aioquic
[aioquic stars]: https://img.shields.io/github/stars/aiortc/aioquic?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[AutoPy]: https://github.com/autopilot-rs/autopy
[AutoPy stars]: https://img.shields.io/github/stars/autopilot-rs/autopy?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[pikepdf]: https://github.com/pikepdf/pikepdf
[pikepdf stars]: https://img.shields.io/github/stars/pikepdf/pikepdf?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[Parselmouth]: https://github.com/YannickJadoul/Parselmouth
[Parselmouth stars]: https://img.shields.io/github/stars/YannickJadoul/Parselmouth?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[KDEpy]: https://github.com/tommyod/KDEpy
[KDEpy stars]: https://img.shields.io/github/stars/tommyod/KDEpy?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[bx-python]: https://github.com/bxlab/bx-python
[bx-python stars]: https://img.shields.io/github/stars/bxlab/bx-python?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[pybase64]: https://github.com/mayeut/pybase64
[pybase64 stars]: https://img.shields.io/github/stars/mayeut/pybase64?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[TgCrypto]: https://github.com/pyrogram/tgcrypto
[TgCrypto stars]: https://img.shields.io/github/stars/pyrogram/tgcrypto?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[etebase-py]: https://github.com/etesync/etebase-py
[etebase-py stars]: https://img.shields.io/github/stars/etesync/etebase-py?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[gmic-py]: https://github.com/dtschump/gmic-py
[gmic-py stars]: https://img.shields.io/github/stars/dtschump/gmic-py?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[fathon]: https://github.com/stfbnc/fathon
[fathon stars]: https://img.shields.io/github/stars/stfbnc/fathon?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[pyinstrument_cext]: https://github.com/joerick/pyinstrument_cext
[pyinstrument_cext stars]: https://img.shields.io/github/stars/joerick/pyinstrument_cext?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[python-admesh]: https://github.com/admesh/python-admesh
[python-admesh stars]: https://img.shields.io/github/stars/admesh/python-admesh?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[xmlstarlet]: https://github.com/dimitern/xmlstarlet
[xmlstarlet stars]: https://img.shields.io/github/stars/dimitern/xmlstarlet?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square
[apriltags2-ethz]: https://github.com/safijari/apriltags2_ethz
[apriltags2-ethz stars]: https://img.shields.io/github/stars/safijari/apriltags2_ethz?color=rgba%28255%2C%20255%2C%20255%2C%200%29&label=%20&logo=reverbnation&logoColor=%23333&style=flat-square

[apple icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/apple.svg
[linux icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/linux.svg
[windows icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/windows.svg
[travisci icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/travisci.svg
[appveyor icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/appveyor.svg
[circleci icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/circleci.svg
[github icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/github.svg
[azure-pipelines icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/azure-pipelines.svg
[gitlab icon]: https://cdn.jsdelivr.net/npm/simple-icons@v4/icons/gitlab.svg

<!-- Matplotlib: 12714, last pushed 0 days ago -->
<!-- twisted-iocpsupport: 4099, last pushed 5 days ago -->
<!-- websockets: 3046, last pushed 3 days ago -->
<!-- aiortc: 2046, last pushed 2 days ago -->
<!-- coverage.py: 1421, last pushed 0 days ago -->
<!-- creme: 1153, last pushed 2 days ago -->
<!-- PyAV: 1105, last pushed 23 days ago -->
<!-- aioquic: 538, last pushed 30 days ago -->
<!-- AutoPy: 500, last pushed 86 days ago -->
<!-- pikepdf: 468, last pushed 3 days ago -->
<!-- Parselmouth: 423, last pushed 7 days ago -->
<!-- KDEpy: 223, last pushed 4 days ago -->
<!-- bx-python: 95, last pushed 67 days ago -->
<!-- pybase64: 51, last pushed 0 days ago -->
<!-- TgCrypto: 48, last pushed 17 days ago -->
<!-- etebase-py: 39, last pushed 3 days ago -->
<!-- gmic-py: 15, last pushed 0 days ago -->
<!-- fathon: 15, last pushed 41 days ago -->
<!-- pyinstrument_cext: 8, last pushed 9 days ago -->
<!-- python-admesh: 8, last pushed 894 days ago -->
<!-- xmlstarlet: 7, last pushed 10 days ago -->
<!-- apriltags2-ethz: 1, last pushed 567 days ago -->


<!-- END bin/project.py -->

> Add your repo here! Send a PR, adding your information to `bin/projects.yml`.
>
> <sup>I'd like to include notes here to indicate why an example might be interesting to cibuildwheel users - the styles/technologies/techniques used in each. Please include that in future additions!</sup>

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

### 1.7.1

_3 December 2020_

- 🛠 Update manylinux2010 image to resolve issues with 'yum' repositories
  (#472)

### 1.7.0

_26 November 2020_

- ✨ New logging format, that uses 'fold groups' in CI services that support
  it. (#458)
- 🛠 Update PyPy to 7.3.3 (#460)
- 🐛 Fix a bug where CIBW_BEFORE_ALL runs with a very old version of Python on
  Linux. (#464)

### 1.6.4

_31 October 2020_

- 🐛 Fix crash on Appveyor during nuget install due to old system CA
  certificates. We now use certifi's CA certs to download files. (#455)

### 1.6.3

_12 October 2020_

- 🐛 Fix missing SSL certificates on macOS (#447)
- 🛠 Update OpenSSL Python 3.5 patch to 1.1.1h on macOS (#449)

### 1.6.2

_9 October 2020_

- ✨ Python 3.9 updated to the final release version - v3.9.0 (#440)
- 🛠 Pypy updated to v7.3.2, adding alpha support for Python 3.7 (#430)

### 1.6.1

_20 September 2020_

- 🛠 Add PPC64LE manylinux image supporting Python 3.9. (#436)
- 📚 Add project URLs to PyPI listing (#428)

### 1.6.0

_9 September 2020_

- 🌟 Add Python 3.9 support! This initial support uses release candidate
  builds. You can start publishing wheels for Python 3.9 now, ahead of
  the official release. (#382)

  Minor note - if you're building PPC64LE wheels, the manylinux image pinned
  by this version is
  [still on Python 3.9b3](https://github.com/pypa/manylinux/issues/758), not a
  release candidate. We'd advise holding off on distributing 3.9 ppc64le wheels
  until a subsequent version of cibuildwheel.
- 🌟 Add Gitlab CI support. Gitlab CI can now build Linux wheels, using
  cibuildwheel. (#419)
- 🐛 Fix a bug that causes pyproject.toml dependencies to fail to install on
  Windows (#420)
- 📚 Added some information about Windows VC++ runtimes and how they relate
  to wheels.

### 1.5.5

_22 July 2020_

- 🐛 Fix a bug that would cause command substitutions in CIBW_ENVIRONMENT to
  produce no output on Linux (#411)
- 🐛 Fix regression (introduced in 1.5.3) which caused BEFORE_BUILD and
  BEFORE_ALL to be executed in the wrong directory (#410)

### 1.5.4

_19 June 2020_

- 🐛 Fix a bug that would cause command substitutions in CIBW_ENVIRONMENT
  variables to not interpret quotes in commands correctly (#406, #408)

### 1.5.3

_19 July 2020_

- 🛠 Update CPython 3.8 to 3.8.3 (#405)
- 🛠 Internal refactoring of Linux build, to move control flow into Python (#386)

### 1.5.2

_8 July 2020_

- 🐛 Fix an issue on Windows where pyproject.toml would cause an error when
  some requirements formats were used. (#401)
- 🛠 Update CPython 3.7 to 3.7.8 (#394)

### 1.5.1

_25 June 2020_

- 🐛 Fix "OSError: [WinError 17] The system cannot move the file to a different
  disk drive" on Github Actions (#388, #389)

### 1.5.0

_24 June 2020_

- 🌟 Add [`CIBW_BEFORE_ALL`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-all)
  option, which lets you run a command on the build machine before any wheels
  are built. This is especially useful when building on Linux, to `make`
  something external to Python, or to `yum install` a dependency. (#342)
- ✨ Added support for projects using pyproject.toml instead of setup.py
  (#360, #358)
- ✨ Added workaround to allow Python 3.5 on Windows to pull dependencies from
  pyproject.toml. (#358)
- 📚 Improved Github Actions examples and docs (#354, #362)
- 🐛 Ensure pip wheel uses the specified package, and doesn't build a wheel
  from PyPI (#369)
- 🛠 Internal changes: using pathlib.Path, precommit hooks, testing
  improvements.

### 1.4.2

_25 May 2020_

- 🛠 Dependency updates, including CPython 3.8.3 & manylinux images.
- 🛠 Lots of internal updates - type annotations and checking using mypy, and
  a new integration testing system.
- ⚠️ Removed support for *running* cibuildwheel using Python 3.5. cibuildwheel
  will continue to build Python 3.5 wheels until EOL.

### 1.4.1

_4 May 2020_

- 🐛 Fix a bug causing programs running inside the i686 manylinux images to
  think they were running x86_64 and target the wrong architecture. (#336,
  #338)

### 1.4.0

_2 May 2020_

- 🌟 Deterministic builds. cibuildwheel now locks the versions of the tools it
  uses. This means that pinning your version of cibuildwheel pins the versions
  of pip, setuptools, manylinux etc. that are used under the hood. This should
  make things more reliable. But note that we don't control the entire build
  environment on macOS and Windows, where the version of Xcode and Visual
  Studio can still effect things.

  This can be controlled using the [CIBW_DEPENDENCY_VERSIONS](https://cibuildwheel.readthedocs.io/en/stable/options/#dependency-versions)
  and [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)
  options - if you always want to use the latest toolchain, you can still do
  that, or you can specify your own pip constraints file and manylinux image.
  (#256)
- ✨ Added `package_dir` command line option, meaning we now support building
  a package that lives in a subdirectory and pulls in files from the wider
  project. See [the `package_dir` option help](https://cibuildwheel.readthedocs.io/en/stable/options/#command-line-options)
  for more information.

  Note that this change makes the working directory (where you call
  cibuildwheel from) relevant on Linux, as it's considered the 'project' and
  will be copied into the Docker container. If your builds are slower on this
  version, that's likely the reason. `cd` to your project and then call
  `cibuildwheel` from there. (#319, #295)
- 🛠 On macOS, we make `MACOSX_DEPLOYMENT_TARGET` default to `10.9` if it's
  not set. This should make things more consistent between Python versions.
- 🛠 Dependency updates - CPython 3.7.7, CPython 2.7.18, Pypy 7.3.1.

### 1.3.0

_12 March 2020_

- 🌟 Add support for building on Github Actions! Check out the
  [docs](https://cibuildwheel.readthedocs.io/en/stable/setup/#github-actions)
  for information on how to set it up. (#194)
- ✨ Add the `CIBW_BEFORE_TEST` option, which lets you run a command to
  prepare the environment before your tests are run. (#242)

### 1.2.0

_8 March 2020_

- 🌟 Add support for building PyPy wheels, across Manylinux, macOS, and
  Windows. (#185)
- 🌟 Added the ability to build ARM64 (aarch64), ppc64le, and s390x wheels,
  using manylinux2014 and Travis CI. (#273)
- ✨ You can now build macOS wheels on Appveyor. (#230)
- 🛠 Changed default macOS minimum target to 10.9, from 10.6. This allows the
  use of more modern C++ libraries, among other things. (#156)
- 🛠 Stop building universal binaries on macOS. We now only build x86_64
  wheels on macOS. (#220)
- ✨ Allow chaining of commands using `&&` and `||` on Windows inside
  CIBW_BEFORE_BUILD and CIBW_TEST_COMMAND. (#293)
- 🛠 Improved error reporting for failed Cython builds due to stale .so files
  (#263)
- 🛠 Update CPython from 3.7.5 to 3.7.6 and from 3.8.0 to 3.8.2 on Mac/Windows
- 🛠 Improved error messages when a bad config breaks cibuildwheel's PATH
  variable. (#264)
- ⚠️ Removed support for *running* cibuildwheel on Python 2.7. cibuildwheel
  will continue to build Python 2.7 wheels for a little while. (#265)

### 1.1.0

_7 December 2019_

- 🌟 Add support for building manylinux2014 wheels. To use, set
  `CIBW_MANYLINUX_X86_64_IMAGE` and CIBW_MANYLINUX_I686_IMAGE to
  `manylinux2014`.
- ✨ Add support for [Linux on Appveyor](https://www.appveyor.com/blog/2018/03/06/appveyor-for-linux/) (#204, #207)
- ✨ Add `CIBW_REPAIR_WHEEL_COMMAND` env variable, for changing how
  `auditwheel` or `delocate` are invoked, or testing an equivalent on
  Windows. (#211)
- 📚 Added some travis example configs - these are available in /examples. (#228)

### 1.0.0

_10 November 2019_

- 🌟 Add support for building Python 3.8 wheels! (#180)
- 🌟 Add support for building manylinux2010 wheels. cibuildwheel will now
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

- 🌟 Add support for building on Azure pipelines! This lets you build all
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

- 🌟 Add `CIBW_BUILD` option, for specifying which specific builds to perform (#101)
- 🌟 Add support for building Mac and Linux on CircleCI (#91, #97)
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
- Henry Schreiner [@henryiii](https://github.com/henryiii)

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
