cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.readthedocs.io/en/stable/?badge=stable) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel) [![Build Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/joerick.cibuildwheel?branchName=master)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=2&branchName=master)

[Documentation](https://cibuildwheel.readthedocs.org)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, and CircleCI - and it builds and tests your wheels across all of your platforms.


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

To build manylinux, macOS, and Windows wheels on Github Actions, you could use this `.github/workflows/wheels.yml`:

```yaml
name: Build

on: [push, pull_request]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-20.04, windows-2019, macOS-10.15]

    steps:
      - uses: actions/checkout@v2

      - uses: actions/setup-python@v2
        name: Install Python

      - name: Install cibuildwheel
        run: python -m pip install cibuildwheel==1.7.3

      - name: Build wheels
        run: python -m cibuildwheel --output-dir wheelhouse
        env:
          CIBW_SKIP: "cp27-* pp27-*"  # skip Python 2.7 wheels

      - uses: actions/upload-artifact@v2
        with:
          path: ./wheelhouse/*.whl
```

For more information, including building on Python 2, PyPI deployment, and the use of other CI services like Travis CI, Appveyor, Azure Pipelines, or CircleCI, check out the [documentation](https://cibuildwheel.readthedocs.org) and the [examples](https://github.com/joerick/cibuildwheel/tree/master/examples).

Options
-------

|   | Option | Description |
|---|--------|-------------|
| **Build selection** | [`CIBW_PLATFORM`](https://cibuildwheel.readthedocs.io/en/stable/options/#platform)  | Override the auto-detected target platform |
|   | [`CIBW_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  <br> [`CIBW_SKIP`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  | Choose the Python versions to build |
| **Build customization** | [`CIBW_ENVIRONMENT`](https://cibuildwheel.readthedocs.io/en/stable/options/#environment)  | Set environment variables needed during the build |
|   | [`CIBW_BEFORE_ALL`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-all)  | Execute a shell command on the build system before any wheels are built. |
|   | [`CIBW_BEFORE_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-build)  | Execute a shell command preparing each wheel's build |
|   | [`CIBW_REPAIR_WHEEL_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#repair-wheel-command)  | Execute a shell command to repair each (non-pure Python) built wheel |
|   | [`CIBW_MANYLINUX_X86_64_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  <br> [`CIBW_MANYLINUX_I686_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  <br> [`CIBW_MANYLINUX_PYPY_X86_64_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  <br> [`CIBW_MANYLINUX_AARCH64_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  <br> [`CIBW_MANYLINUX_PPC64LE_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  <br> [`CIBW_MANYLINUX_S390X_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  | Specify alternative manylinux docker images |
|   | [`CIBW_DEPENDENCY_VERSIONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#dependency-versions)  | Specify how cibuildwheel controls the versions of the tools it uses |
| **Testing** | [`CIBW_TEST_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-command)  | Execute a shell command to test each built wheel |
|   | [`CIBW_BEFORE_TEST`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-test)  | Execute a shell command before testing each wheel |
|   | [`CIBW_TEST_REQUIRES`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-requires)  | Install Python dependencies before running the tests |
|   | [`CIBW_TEST_EXTRAS`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-extras)  | Install your wheel for testing using extras_require |
| **Other** | [`CIBW_BUILD_VERBOSITY`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-verbosity)  | Increase/decrease the output of pip wheel |


Working examples
----------------

<!--working-examples-start-->

Here are some repos that use cibuildwheel.

<!-- START bin/projects.py -->

<!-- this section is generated by bin/projects.py. Don't edit it directly, instead, edit docs/data/projects.yml -->

| Name                              | CI | OS | Notes |
|-----------------------------------|----|----|:------|
| [scikit-learn][]                  | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The machine learning library. A complex but clean config using many of cibuildwheel's features to build a large project with Cython and C++ extensions.  |
| [Matplotlib][]                    | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The venerable Matplotlib, a Python library with C++ portions |
| [psutil][]                        | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Cross-platform lib for process and system monitoring in Python |
| [twisted-iocpsupport][]           | ![github icon][] | ![windows icon][] | A submodule of Twisted that hooks into native C APIs using Cython. |
| [scikit-image][]                  | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Image processing library. Uses cibuildwheel to build and test a project that uses Cython with platform-native code.  |
| [websockets][]                    | ![travisci icon][] | ![apple icon][] ![linux icon][] | Library for building WebSocket servers and clients. Mostly written in Python, with a small C 'speedups' extension module.  |
| [pyzmq][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Python bindings for zeromq, the networking library. Uses Cython and CFFI.  |
| [aiortc][]                        | ![github icon][] | ![apple icon][] ![linux icon][] | WebRTC and ORTC implementation for Python using asyncio. |
| [h5py][]                          | ![azurepipelines icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | HDF5 for Python -- The h5py package is a Pythonic interface to the HDF5 binary data format. |
| [coverage.py][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The coverage tool for Python |
| [River][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | 🌊 Online machine learning in Python |
| [PyAV][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Pythonic bindings for FFmpeg's libraries. |
| [Dependency Injector][]           | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Dependency injection framework for Python, uses Windows TravisCI |
| [aioquic][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | QUIC and HTTP/3 implementation in Python |
| [google neuroglancer][]           | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | WebGL-based viewer for volumetric data |
| [AutoPy][]                        | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Includes a Windows Travis build. |
| [pikepdf][]                       | ![azurepipelines icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python library for reading and writing PDF, powered by qpdf |
| [Parselmouth][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python interface to the Praat software package, using pybind11, C++17 and CMake, with the core Praat static library built only once and shared between wheels. |
| [python-rapidjson][]              | ![travisci icon][] ![gitlab icon][] ![appveyor icon][] | ![windows icon][] ![linux icon][] | Python wrapper around rapidjson |
| [Rtree][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Rtree: spatial index for Python GIS ¶ |
| [KDEpy][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Kernel Density Estimation in Python |
| [pybind11 python_example][]       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a Python-based build system |
| [pybind11 cmake_example][]        | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a CMake-based build system |
| [iminuit][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Jupyter-friendly Python interface for C++ MINUIT2 |
| [jq.py][]                         | ![travisci icon][] | ![apple icon][] ![linux icon][] | Python bindings for jq |
| [bx-python][]                     | ![travisci icon][] | ![apple icon][] ![linux icon][] | A library that includes Cython extensions. |
| [boost-histogram][]               | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Supports full range of wheels, including PyPy and alternate archs. |
| [pybase64][]                      | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Fast Base64 encoding/decoding in Python |
| [TgCrypto][]                      | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Includes a Windows Travis build. |
| [etebase-py][]                    | ![travisci icon][] | ![linux icon][] | Python bindings to a Rust library using `setuptools-rust`, and `sccache` for improved speed. |
| [pyjet][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The interface between FastJet and NumPy |
| [numpythia][]                     | ![github icon][] | ![apple icon][] ![linux icon][] | The interface between PYTHIA and NumPy |
| [fathon][]                        | ![travisci icon][] | ![apple icon][] ![linux icon][] | python package for DFA (Detrended Fluctuation Analysis) and related algorithms |
| [pyinstrument_cext][]             | ![travisci icon][] ![appveyor icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A simple C extension, without external dependencies |
| [xmlstarlet][]                    | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Python 3.6+ CFFI bindings with true MSVC build. |
| [pybind11 scikit_build_example][] | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | An example combining scikit-build and pybind11 |

[scikit-learn]: https://github.com/scikit-learn/scikit-learn
[Matplotlib]: https://github.com/matplotlib/matplotlib
[psutil]: https://github.com/giampaolo/psutil
[twisted-iocpsupport]: https://github.com/twisted/twisted-iocpsupport
[scikit-image]: https://github.com/scikit-image/scikit-image
[websockets]: https://github.com/aaugustin/websockets
[pyzmq]: https://github.com/zeromq/pyzmq
[aiortc]: https://github.com/aiortc/aiortc
[h5py]: https://github.com/h5py/h5py
[coverage.py]: https://github.com/nedbat/coveragepy
[River]: https://github.com/online-ml/river
[PyAV]: https://github.com/PyAV-Org/PyAV
[Dependency Injector]: https://github.com/ets-labs/python-dependency-injector
[aioquic]: https://github.com/aiortc/aioquic
[google neuroglancer]: https://github.com/google/neuroglancer
[AutoPy]: https://github.com/autopilot-rs/autopy
[pikepdf]: https://github.com/pikepdf/pikepdf
[Parselmouth]: https://github.com/YannickJadoul/Parselmouth
[python-rapidjson]: https://github.com/python-rapidjson/python-rapidjson
[Rtree]: https://github.com/Toblerity/rtree
[KDEpy]: https://github.com/tommyod/KDEpy
[pybind11 python_example]: https://github.com/pybind/python_example
[pybind11 cmake_example]: https://github.com/pybind/cmake_example
[iminuit]: https://github.com/scikit-hep/iminuit
[jq.py]: https://github.com/mwilliamson/jq.py
[bx-python]: https://github.com/bxlab/bx-python
[boost-histogram]: https://github.com/scikit-hep/boost-histogram
[pybase64]: https://github.com/mayeut/pybase64
[TgCrypto]: https://github.com/pyrogram/tgcrypto
[etebase-py]: https://github.com/etesync/etebase-py
[pyjet]: https://github.com/scikit-hep/pyjet
[numpythia]: https://github.com/scikit-hep/numpythia
[fathon]: https://github.com/stfbnc/fathon
[pyinstrument_cext]: https://github.com/joerick/pyinstrument_cext
[xmlstarlet]: https://github.com/dimitern/xmlstarlet
[pybind11 scikit_build_example]: https://github.com/pybind/scikit_build_example

[appveyor icon]: docs/data/readme_icons/appveyor.svg
[github icon]: docs/data/readme_icons/github.svg
[azurepipelines icon]: docs/data/readme_icons/azurepipelines.svg
[circleci icon]: docs/data/readme_icons/circleci.svg
[gitlab icon]: docs/data/readme_icons/gitlab.svg
[travisci icon]: docs/data/readme_icons/travisci.svg
[windows icon]: docs/data/readme_icons/windows.svg
[apple icon]: docs/data/readme_icons/apple.svg
[linux icon]: docs/data/readme_icons/linux.svg

<!-- scikit-learn: 43477, last pushed 0 days ago -->
<!-- Matplotlib: 12823, last pushed 0 days ago -->
<!-- psutil: 6887, last pushed 0 days ago -->
<!-- twisted-iocpsupport: 4114, last pushed 2 days ago -->
<!-- scikit-image: 4104, last pushed 0 days ago -->
<!-- websockets: 3089, last pushed 10 days ago -->
<!-- pyzmq: 2654, last pushed 20 days ago -->
<!-- aiortc: 2073, last pushed 7 days ago -->
<!-- h5py: 1455, last pushed 12 days ago -->
<!-- coverage.py: 1441, last pushed 3 days ago -->
<!-- River: 1219, last pushed 0 days ago -->
<!-- PyAV: 1114, last pushed 14 days ago -->
<!-- Dependency Injector: 1030, last pushed 0 days ago -->
<!-- aioquic: 552, last pushed 49 days ago -->
<!-- google neuroglancer: 550, last pushed 7 days ago -->
<!-- AutoPy: 507, last pushed 105 days ago -->
<!-- pikepdf: 487, last pushed 0 days ago -->
<!-- Parselmouth: 433, last pushed 26 days ago -->
<!-- python-rapidjson: 407, last pushed 10 days ago -->
<!-- Rtree: 378, last pushed 0 days ago -->
<!-- KDEpy: 230, last pushed 9 days ago -->
<!-- pybind11 python_example: 221, last pushed 44 days ago -->
<!-- pybind11 cmake_example: 219, last pushed 7 days ago -->
<!-- iminuit: 166, last pushed 0 days ago -->
<!-- jq.py: 138, last pushed 73 days ago -->
<!-- bx-python: 94, last pushed 1 days ago -->
<!-- boost-histogram: 63, last pushed 0 days ago -->
<!-- pybase64: 52, last pushed 2 days ago -->
<!-- TgCrypto: 49, last pushed 36 days ago -->
<!-- etebase-py: 40, last pushed 3 days ago -->
<!-- pyjet: 27, last pushed 29 days ago -->
<!-- numpythia: 23, last pushed 28 days ago -->
<!-- fathon: 18, last pushed 1 days ago -->
<!-- pyinstrument_cext: 10, last pushed 29 days ago -->
<!-- xmlstarlet: 7, last pushed 0 days ago -->
<!-- pybind11 scikit_build_example: 0, last pushed 42 days ago -->

<!-- END bin/projects.py -->

> Add your repo here! Send a PR, adding your information to `docs/data/projects.yml`.
>
> <sup>I'd like to include notes here to indicate why an example might be interesting to cibuildwheel users - the styles/technologies/techniques used in each. Please include that in future additions!</sup>

<!--working-examples-end-->

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

<!--changelog-start-->

### 1.7.3

_1 January 2021_

- 🛠 Added a patch for Pypy to ensure header files are available for building
  in a virtualenv. (#502)
- 🛠 Some preparatory work towards using cibuildwheel as a Github Action.
  Check out
  [the FAQ](https://cibuildwheel.readthedocs.io/en/stable/faq/#option-1-github-action)
  for information on how to use it. We'll be fully updating the docs to this
  approach in a subsequent release (#494)

### 1.7.2

_21 December 2020_

- 🛠 Update dependencies, notably wheel==0.36.2 and pip==20.3.3, and CPython to
  their latest bugfix releases (#489)
- 📚 Switch to a Github example in the README (#479)
- 📚 Create Working Examples table, with many projects that use cibuildwheel (#474)
- 📚 Import Working Examples table and Changelog to docs

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

<!--changelog-end-->

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

Another very similar tool to consider is [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a shell script toolbox for building a wheel on various platforms. It is used as a basis to build some of the big data science tools, like SciPy.
