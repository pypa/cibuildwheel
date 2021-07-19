cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel)
[![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.readthedocs.io/en/stable/?badge=stable)
[![Actions Status](https://github.com/pypa/cibuildwheel/workflows/Test/badge.svg)](https://github.com/pypa/cibuildwheel/actions)
[![Travis Status](https://img.shields.io/travis/com/pypa/cibuildwheel/main?logo=travis)](https://travis-ci.com/pypa/cibuildwheel)
[![Appveyor status](https://ci.appveyor.com/api/projects/status/gt3vwl88yt0y3hur/branch/main?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/main)
[![CircleCI Status](https://img.shields.io/circleci/build/gh/pypa/cibuildwheel/main?logo=circleci)](https://circleci.com/gh/pypa/cibuildwheel)
[![Azure Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/pypa.cibuildwheel?branchName=main)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=4&branchName=main)


[Documentation](https://cibuildwheel.readthedocs.org)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, and GitLab CI - and it builds and tests your wheels across all of your platforms.


What does it do?
----------------

|   | macOS Intel | macOS Apple Silicon | Windows 64bit | Windows 32bit | manylinux x86_64 | manylinux i686 | manylinux aarch64 | manylinux ppc64le | manylinux s390x |
|---------------|----|-----|-----|-----|----|-----|----|-----|-----|
| CPython 3.6   | ✅ | N/A | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.7   | ✅ | N/A | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.8   | ✅ | ✅  | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.9   | ✅ | ✅  | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.10¹ | ✅ | ✅  | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| PyPy 3.7 v7.3 | ✅ | N/A | ✅  | N/A | ✅ | ✅  | ✅ | N/A | N/A |

<sup>¹ Available as a prerelease under a [flag](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons)</sup><br>

- Builds manylinux, macOS 10.9+, and Windows wheels for CPython and PyPy
- Works on GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, and GitLab CI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs your library's tests against the wheel-installed version of your library

See the [cibuildwheel 1 documentation](https://cibuildwheel.readthedocs.io/en/1.x/) if you need to build unsupported versions of Python, such as Python 2.

Usage
-----

`cibuildwheel` runs inside a CI service. Supported platforms depend on which service you're using:

|                 | Linux | macOS | Windows | Linux ARM |
|-----------------|-------|-------|---------|--------------|
| GitHub Actions  | ✅    | ✅    | ✅      | ✅¹          |
| Azure Pipelines | ✅    | ✅    | ✅      |              |
| Travis CI       | ✅    |       | ✅      | ✅           |
| AppVeyor        | ✅    | ✅    | ✅      |              |
| CircleCI        | ✅    | ✅    |         |              |
| Gitlab CI       | ✅    |       |         |              |

<sup>¹ [Requires emulation](https://cibuildwheel.readthedocs.io/en/stable/faq/#emulation), distributed separately. Other services may also support Linux ARM through emulation or third-party build hosts, but these are not tested in our CI.</sup><br>

`cibuildwheel` is not intended to run on your development machine. Because it uses system Python from Python.org on macOS and Windows, it will try to install packages globally - not what you expect from a build tool! Instead, isolated CI services like those mentioned above are ideal. For Linux builds, it uses manylinux docker images, so those can be done locally for testing in a pinch.

<!--intro-end-->

Example setup
-------------

To build manylinux, macOS, and Windows wheels on GitHub Actions, you could use this `.github/workflows/wheels.yml`:

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

      # Used to host cibuildwheel
      - uses: actions/setup-python@v2

      - name: Install cibuildwheel
        run: python -m pip install cibuildwheel==2.0.0

      - name: Build wheels
        run: python -m cibuildwheel --output-dir wheelhouse
        # to supply options, put them in 'env', like:
        # env:
        #   CIBW_SOME_OPTION: value

      - uses: actions/upload-artifact@v2
        with:
          path: ./wheelhouse/*.whl
```

For more information, including PyPI deployment, and the use of other CI services or the dedicated GitHub Action, check out the [documentation](https://cibuildwheel.readthedocs.org) and the [examples](https://github.com/pypa/cibuildwheel/tree/main/examples).

Options
-------

|   | Option | Description |
|---|--------|-------------|
| **Build selection** | [`CIBW_PLATFORM`](https://cibuildwheel.readthedocs.io/en/stable/options/#platform)  | Override the auto-detected target platform |
|   | [`CIBW_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  <br> [`CIBW_SKIP`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip)  | Choose the Python versions to build |
|   | [`CIBW_ARCHS`](https://cibuildwheel.readthedocs.io/en/stable/options/#archs)  | Change the architectures built on your machine by default. |
|   | [`CIBW_PROJECT_REQUIRES_PYTHON`](https://cibuildwheel.readthedocs.io/en/stable/options/#requires-python)  | Manually set the Python compatibility of your project |
|   | [`CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons)  | Enable building with pre-release versions of Python |
| **Build customization** | [`CIBW_BUILD_FRONTEND`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-frontend)  | Set the tool to use to build, either "pip" (default for now) or "build" |
|   | [`CIBW_ENVIRONMENT`](https://cibuildwheel.readthedocs.io/en/stable/options/#environment)  | Set environment variables needed during the build |
|   | [`CIBW_BEFORE_ALL`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-all)  | Execute a shell command on the build system before any wheels are built. |
|   | [`CIBW_BEFORE_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-build)  | Execute a shell command preparing each wheel's build |
|   | [`CIBW_REPAIR_WHEEL_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#repair-wheel-command)  | Execute a shell command to repair each (non-pure Python) built wheel |
|   | [`CIBW_MANYLINUX_*_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)  | Specify alternative manylinux Docker images |
|   | [`CIBW_DEPENDENCY_VERSIONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#dependency-versions)  | Specify how cibuildwheel controls the versions of the tools it uses |
| **Testing** | [`CIBW_TEST_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-command)  | Execute a shell command to test each built wheel |
|   | [`CIBW_BEFORE_TEST`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-test)  | Execute a shell command before testing each wheel |
|   | [`CIBW_TEST_REQUIRES`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-requires)  | Install Python dependencies before running the tests |
|   | [`CIBW_TEST_EXTRAS`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-extras)  | Install your wheel for testing using extras_require |
|   | [`CIBW_TEST_SKIP`](https://cibuildwheel.readthedocs.io/en/stable/options/#test-skip)  | Skip running tests on some builds |
| **Other** | [`CIBW_BUILD_VERBOSITY`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-verbosity)  | Increase/decrease the output of pip wheel |

These options can be specified in a pyproject.toml file, as well; see [configuration](https://cibuildwheel.readthedocs.io/en/stable/options/#configuration).

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
| [MyPy][]                          | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | MyPyC, the compiled component of MyPy. |
| [psutil][]                        | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Cross-platform lib for process and system monitoring in Python |
| [scikit-image][]                  | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Image processing library. Uses cibuildwheel to build and test a project that uses Cython with platform-native code.  |
| [twisted-iocpsupport][]           | ![github icon][] | ![windows icon][] | A submodule of Twisted that hooks into native C APIs using Cython. |
| [cmake][]                         | ![github icon][] ![travisci icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Multitagged binary builds for all supported platforms, using cibw 2 config configuration. |
| [websockets][]                    | ![travisci icon][] | ![apple icon][] ![linux icon][] | Library for building WebSocket servers and clients. Mostly written in Python, with a small C 'speedups' extension module.  |
| [pyzmq][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Python bindings for zeromq, the networking library. Uses Cython and CFFI.  |
| [aiortc][]                        | ![github icon][] | ![apple icon][] ![linux icon][] | WebRTC and ORTC implementation for Python using asyncio. |
| [River][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | 🌊 Online machine learning in Python |
| [coverage.py][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The coverage tool for Python |
| [numexpr][]                       | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Fast numerical array expression evaluator for Python, NumPy, PyTables, pandas, bcolz and more |
| [h5py][]                          | ![azurepipelines icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | HDF5 for Python -- The h5py package is a Pythonic interface to the HDF5 binary data format. |
| [Dependency Injector][]           | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Dependency injection framework for Python, uses Windows TravisCI |
| [PyAV][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Pythonic bindings for FFmpeg's libraries. |
| [PyTables][]                      | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python package to manage extremely large amounts of data |
| [ruptures][]                      | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Extensive Cython + NumPy [pyproject.toml](https://github.com/deepcharles/ruptures/blob/master/pyproject.toml) example. |
| [aioquic][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | QUIC and HTTP/3 implementation in Python |
| [pikepdf][]                       | ![azurepipelines icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python library for reading and writing PDF, powered by qpdf |
| [google neuroglancer][]           | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | WebGL-based viewer for volumetric data |
| [DeepForest][]                    | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | An Efficient, Scalable and Optimized Python Framework for Deep Forest (2021.2.1) |
| [AutoPy][]                        | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Includes a Windows Travis build. |
| [Parselmouth][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python interface to the Praat software package, using pybind11, C++17 and CMake, with the core Praat static library built only once and shared between wheels. |
| [python-rapidjson][]              | ![travisci icon][] ![gitlab icon][] ![appveyor icon][] | ![windows icon][] ![linux icon][] | Python wrapper around rapidjson |
| [Rtree][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Rtree: spatial index for Python GIS ¶ |
| [python-snappy][]                 | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Python bindings for the snappy google library |
| [markupsafe][]                    | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Safely add untrusted strings to HTML/XML markup. |
| [H3-py][]                         | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Python bindings for H3, a hierarchical hexagonal geospatial indexing system |
| [pybind11 cmake_example][]        | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a CMake-based build system |
| [KDEpy][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Kernel Density Estimation in Python |
| [cyvcf2][]                        | ![github icon][] | ![apple icon][] ![linux icon][] | cython + htslib == fast VCF and BCF processing |
| [pybind11 python_example][]       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a Python-based build system |
| [dd-trace-py][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Uses custom alternate arch emulation on GitHub |
| [sourmash][]                      | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Quickly search, compare, and analyze genomic and metagenomic data sets. |
| [time-machine][]                  | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Time mocking library using only the CPython C API. |
| [iminuit][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Jupyter-friendly Python interface for C++ MINUIT2 |
| [CTranslate2][]                   | ![github icon][] | ![apple icon][] ![linux icon][] | Includes libraries from the [Intel oneAPI toolkit](https://software.intel.com/content/www/us/en/develop/tools/oneapi/base-toolkit.html). The Linux wheels also include CUDA libraries for GPU execution. |
| [matrixprofile][]                 | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python 3 library making time series data mining tasks, utilizing matrix profile algorithms, accessible to everyone. |
| [jq.py][]                         | ![travisci icon][] | ![apple icon][] ![linux icon][] | Python bindings for jq |
| [Tokenizer][]                     | ![github icon][] ![travisci icon][] | ![apple icon][] ![linux icon][] | Fast and customizable text tokenization library with BPE and SentencePiece support |
| [PyGLM][]                         | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Fast OpenGL Mathematics (GLM) for Python |
| [bx-python][]                     | ![travisci icon][] | ![apple icon][] ![linux icon][] | A library that includes Cython extensions. |
| [boost-histogram][]               | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Supports full range of wheels, including PyPy and alternate archs. |
| [iDynTree][]                      | ![github icon][] | ![linux icon][] | Uses manylinux_2_24 |
| [pybase64][]                      | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Fast Base64 encoding/decoding in Python |
| [TgCrypto][]                      | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Includes a Windows Travis build. |
| [etebase-py][]                    | ![travisci icon][] | ![linux icon][] | Python bindings to a Rust library using `setuptools-rust`, and `sccache` for improved speed. |
| [fathon][]                        | ![travisci icon][] | ![apple icon][] ![linux icon][] | python package for DFA (Detrended Fluctuation Analysis) and related algorithms |
| [pyjet][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The interface between FastJet and NumPy |
| [numpythia][]                     | ![github icon][] | ![apple icon][] ![linux icon][] | The interface between PYTHIA and NumPy |
| [polaroid][]                      | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Full range of wheels for setuptools rust, with auto release and PyPI deploy. |
| [ninja][]                         | ![github icon][] ![travisci icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Multitagged binary builds for all supported platforms, using cibw 2 config configuration. |
| [GSD][]                           | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Cython and NumPy project with 64-bit wheels. |
| [pybind11 scikit_build_example][] | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | An example combining scikit-build and pybind11 |
| [Imagecodecs (fork)][]            | ![azurepipelines icon][] | ![apple icon][] ![linux icon][] | Over 20 external dependencies in compiled libraries, custom docker image, `libomp`, `openblas` and `install_name_tool` for macOS. |
| [pyinstrument_cext][]             | ![travisci icon][] ![appveyor icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A simple C extension, without external dependencies |
| [xmlstarlet][]                    | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Python 3.6+ CFFI bindings with true MSVC build. |
| [CorrectionLib][]                 | ![github icon][] | ![apple icon][] ![linux icon][] | Structured JSON powered correction library for HEP, designed for the CMS experiment at CERN. |
| [SiPM][]                          | ![github icon][] | ![apple icon][] ![linux icon][] | High performance library for SiPM detectors simulation using C++17, OpenMP and AVX2 intrinsics. |

[scikit-learn]: https://github.com/scikit-learn/scikit-learn
[Matplotlib]: https://github.com/matplotlib/matplotlib
[MyPy]: https://github.com/mypyc/mypy_mypyc-wheels
[psutil]: https://github.com/giampaolo/psutil
[scikit-image]: https://github.com/scikit-image/scikit-image
[twisted-iocpsupport]: https://github.com/twisted/twisted-iocpsupport
[cmake]: https://github.com/scikit-build/cmake-python-distributions
[websockets]: https://github.com/aaugustin/websockets
[pyzmq]: https://github.com/zeromq/pyzmq
[aiortc]: https://github.com/aiortc/aiortc
[River]: https://github.com/online-ml/river
[coverage.py]: https://github.com/nedbat/coveragepy
[numexpr]: https://github.com/pydata/numexpr
[h5py]: https://github.com/h5py/h5py
[Dependency Injector]: https://github.com/ets-labs/python-dependency-injector
[PyAV]: https://github.com/PyAV-Org/PyAV
[PyTables]: https://github.com/PyTables/PyTables
[ruptures]: https://github.com/deepcharles/ruptures
[aioquic]: https://github.com/aiortc/aioquic
[pikepdf]: https://github.com/pikepdf/pikepdf
[google neuroglancer]: https://github.com/google/neuroglancer
[DeepForest]: https://github.com/LAMDA-NJU/Deep-Forest
[AutoPy]: https://github.com/autopilot-rs/autopy
[Parselmouth]: https://github.com/YannickJadoul/Parselmouth
[python-rapidjson]: https://github.com/python-rapidjson/python-rapidjson
[Rtree]: https://github.com/Toblerity/rtree
[python-snappy]: https://github.com/andrix/python-snappy
[markupsafe]: https://github.com/pallets/markupsafe
[H3-py]: https://github.com/uber/h3-py
[pybind11 cmake_example]: https://github.com/pybind/cmake_example
[KDEpy]: https://github.com/tommyod/KDEpy
[cyvcf2]: https://github.com/brentp/cyvcf2
[pybind11 python_example]: https://github.com/pybind/python_example
[dd-trace-py]: https://github.com/DataDog/dd-trace-py
[sourmash]: https://github.com/dib-lab/sourmash
[time-machine]: https://github.com/adamchainz/time-machine
[iminuit]: https://github.com/scikit-hep/iminuit
[CTranslate2]: https://github.com/OpenNMT/CTranslate2
[matrixprofile]: https://github.com/matrix-profile-foundation/matrixprofile
[jq.py]: https://github.com/mwilliamson/jq.py
[Tokenizer]: https://github.com/OpenNMT/Tokenizer
[PyGLM]: https://github.com/Zuzu-Typ/PyGLM
[bx-python]: https://github.com/bxlab/bx-python
[boost-histogram]: https://github.com/scikit-hep/boost-histogram
[iDynTree]: https://github.com/robotology/idyntree
[pybase64]: https://github.com/mayeut/pybase64
[TgCrypto]: https://github.com/pyrogram/tgcrypto
[etebase-py]: https://github.com/etesync/etebase-py
[fathon]: https://github.com/stfbnc/fathon
[pyjet]: https://github.com/scikit-hep/pyjet
[numpythia]: https://github.com/scikit-hep/numpythia
[polaroid]: https://github.com/daggy1234/polaroid
[ninja]: https://github.com/scikit-build/ninja-python-distributions
[GSD]: https://github.com/glotzerlab/gsd
[pybind11 scikit_build_example]: https://github.com/pybind/scikit_build_example
[Imagecodecs (fork)]: https://github.com/czaki/imagecodecs_build
[pyinstrument_cext]: https://github.com/joerick/pyinstrument_cext
[xmlstarlet]: https://github.com/dimitern/xmlstarlet
[CorrectionLib]: https://github.com/cms-nanoAOD/correctionlib
[SiPM]: https://github.com/EdoPro98/SimSiPM

[appveyor icon]: docs/data/readme_icons/appveyor.svg
[github icon]: docs/data/readme_icons/github.svg
[azurepipelines icon]: docs/data/readme_icons/azurepipelines.svg
[circleci icon]: docs/data/readme_icons/circleci.svg
[gitlab icon]: docs/data/readme_icons/gitlab.svg
[travisci icon]: docs/data/readme_icons/travisci.svg
[windows icon]: docs/data/readme_icons/windows.svg
[apple icon]: docs/data/readme_icons/apple.svg
[linux icon]: docs/data/readme_icons/linux.svg

<!-- scikit-learn: 46430, last pushed 0 days ago -->
<!-- Matplotlib: 13903, last pushed 0 days ago -->
<!-- MyPy: 11014, last pushed 0 days ago -->
<!-- psutil: 7484, last pushed 15 days ago -->
<!-- scikit-image: 4419, last pushed 0 days ago -->
<!-- twisted-iocpsupport: 4296, last pushed 0 days ago -->
<!-- cmake: 4013, last pushed 0 days ago -->
<!-- websockets: 3457, last pushed 19 days ago -->
<!-- pyzmq: 2848, last pushed 6 days ago -->
<!-- aiortc: 2470, last pushed 4 days ago -->
<!-- River: 1749, last pushed 3 days ago -->
<!-- coverage.py: 1646, last pushed 0 days ago -->
<!-- numexpr: 1605, last pushed 8 days ago -->
<!-- h5py: 1540, last pushed 3 days ago -->
<!-- Dependency Injector: 1447, last pushed 21 days ago -->
<!-- PyAV: 1295, last pushed 39 days ago -->
<!-- PyTables: 1042, last pushed 112 days ago -->
<!-- ruptures: 757, last pushed 9 days ago -->
<!-- aioquic: 708, last pushed 1 days ago -->
<!-- pikepdf: 683, last pushed 2 days ago -->
<!-- google neuroglancer: 661, last pushed 0 days ago -->
<!-- DeepForest: 629, last pushed 0 days ago -->
<!-- AutoPy: 550, last pushed 28 days ago -->
<!-- Parselmouth: 524, last pushed 22 days ago -->
<!-- python-rapidjson: 425, last pushed 20 days ago -->
<!-- Rtree: 413, last pushed 117 days ago -->
<!-- python-snappy: 405, last pushed 140 days ago -->
<!-- markupsafe: 404, last pushed 9 days ago -->
<!-- H3-py: 402, last pushed 33 days ago -->
<!-- pybind11 cmake_example: 289, last pushed 6 days ago -->
<!-- KDEpy: 285, last pushed 42 days ago -->
<!-- cyvcf2: 264, last pushed 77 days ago -->
<!-- pybind11 python_example: 258, last pushed 1 days ago -->
<!-- dd-trace-py: 256, last pushed 0 days ago -->
<!-- sourmash: 253, last pushed 0 days ago -->
<!-- time-machine: 187, last pushed 2 days ago -->
<!-- iminuit: 180, last pushed 11 days ago -->
<!-- CTranslate2: 177, last pushed 0 days ago -->
<!-- matrixprofile: 170, last pushed 20 days ago -->
<!-- jq.py: 162, last pushed 23 days ago -->
<!-- Tokenizer: 148, last pushed 20 days ago -->
<!-- PyGLM: 106, last pushed 65 days ago -->
<!-- bx-python: 103, last pushed 6 days ago -->
<!-- boost-histogram: 82, last pushed 3 days ago -->
<!-- iDynTree: 82, last pushed 0 days ago -->
<!-- pybase64: 68, last pushed 0 days ago -->
<!-- TgCrypto: 67, last pushed 46 days ago -->
<!-- etebase-py: 51, last pushed 192 days ago -->
<!-- fathon: 32, last pushed 43 days ago -->
<!-- pyjet: 29, last pushed 57 days ago -->
<!-- numpythia: 29, last pushed 6 days ago -->
<!-- polaroid: 19, last pushed 17 days ago -->
<!-- ninja: 19, last pushed 0 days ago -->
<!-- GSD: 16, last pushed 14 days ago -->
<!-- pybind11 scikit_build_example: 14, last pushed 6 days ago -->
<!-- Imagecodecs (fork): 11, last pushed 20 days ago -->
<!-- pyinstrument_cext: 10, last pushed 15 days ago -->
<!-- xmlstarlet: 7, last pushed 3 days ago -->
<!-- CorrectionLib: 6, last pushed 23 days ago -->
<!-- SiPM: 4, last pushed 6 days ago -->

<!-- END bin/projects.py -->

> Add your repo here! Let us know on [GitHub Discussions](https://github.com/pypa/cibuildwheel/discussions/485), or send a PR, adding your information to `docs/data/projects.yml`.
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

<!-- START bin/update_readme_changelog.py -->

<!-- this section was generated by bin/update_readme_changelog.py -- do not edit manually -->

### v2.0.0 🎉

_16 July 2021_

- 🌟 You can now configure cibuildwheel options inside your project's `pyproject.toml`! Environment variables still work of course. Check out the [documentation](https://cibuildwheel.readthedocs.io/en/stable/options/#setting-options) for more info.
- 🌟 Added support for building wheels with [build](https://github.com/pypa/build), as well as pip. This feature is controlled with the [`CIBW_BUILD_FRONTEND`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-frontend) option.
- 🌟 Added the ability to test building wheels on CPython 3.10! Because CPython 3.10 is in beta, these wheels should not be distributed, because they might not be compatible with the final release, but it's available to build for testing purposes. Use the flag [`--prerelease-pythons` or `CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons) to test. (#675) This version of cibuildwheel includes CPython 3.10.0b4.
- ⚠️ **Removed support for building Python 2.7 and Python 3.5 wheels**, for both CPython and PyPy. If you still need to build on these versions, please use the latest v1.x version. (#596)
- ✨ Added the ability to build CPython 3.8 wheels for Apple Silicon. (#704)
- 🛠 Update to the latest build dependencies, including Auditwheel 4. (#633)
- 🛠 Use the unified pypa/manylinux images to build PyPy (#671)
- 🐛 Numerous bug fixes & docs improvements

### v1.12.0

_22 June 2021_

- ✨ Adds support building macOS universal2/arm64 wheels on Python 3.8.

### v1.11.1

_28 May 2021_

- ✨ cibuildwheel is now part of the PyPA!
- 📚 Minor docs changes, fixing links related to the above transition
- 🛠 Update manylinux pins to the last version containing Python 2.7 and 3.5. (#674)

### v1.11.0

_1 May 2021_

- 📚 Lots of docs improvements! (#650, #623, #616, #609, #606)
- 🐛 Fix nuget "Package is not found" error on Windows. (#653)
- ⚠️ cibuildwheel will no longer build Windows 2.7 wheels, unless you specify a custom toolchain using `DISTUTILS_USE_SDK=1` and `MSSdk=1`. This is because Microsoft have stopped distributing Visual C++ Compiler for Python 2.7. See [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#windows-and-python-27) for more details. (#649)
- 🐛 Fix crash on Windows due to missing `which` command (#641).

### v1.10.0

_22 Feb 2021_

- ✨ Added `manylinux_2_24` support. To use these new Debian-based manylinux
  images, set your [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)
  options to `manylinux_2_24`.
- 🛠 On macOS, we now set `MACOSX_DEPLOYMENT_TARGET` in before running
  `CIBW_BEFORE_ALL`. This is useful when using `CIBW_BEFORE_ALL` to build a
  shared library.
- 🛠 An empty `CIBW_BUILD` option is now the same as being unset i.e, `*`.
  This makes some build matrix configuration easier. (#588)
- 📚 Neatened up documentation - added tabs to a few places (#576), fixed some
  formatting issues.

<!-- END bin/update_readme_changelog.py -->

---

That's the last few versions.

ℹ️ **Want more changelog? Head over to [the changelog page in the docs](https://cibuildwheel.readthedocs.io/en/stable/changelog/).**

---

Contributing
============

For more info on how to contribute to cibuildwheel, see the [docs](https://cibuildwheel.readthedocs.io/en/latest/contributing/).

Everyone interacting with the cibuildwheel project via codebase, issue tracker, chat rooms, or otherwise is expected to follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).

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

- @zfrenchee for [help debugging many issues](https://github.com/pypa/cibuildwheel/issues/2)
- @lelit for some great bug reports and [contributions](https://github.com/pypa/cibuildwheel/pull/73)
- @mayeut for a [phenomenal PR](https://github.com/pypa/cibuildwheel/pull/71) patching Python itself for better compatibility!
- @czaki for being a super-contributor over many PRs and helping out with countless issues!
- @mattip for his help with adding PyPy support to cibuildwheel

See also
========

If you'd like to keep wheel building separate from the package itself, check out [astrofrog/autowheel](https://github.com/astrofrog/autowheel). It builds packages using cibuildwheel from source distributions on PyPI.

Another very similar tool to consider is [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a shell script toolbox for building a wheel on various platforms. It is used as a basis to build some of the big data science tools, like SciPy.
