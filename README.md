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
        run: python -m pip install cibuildwheel==2.1.1

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
| [markupsafe][]                    | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Safely add untrusted strings to HTML/XML markup. |
| [python-snappy][]                 | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Python bindings for the snappy google library |
| [H3-py][]                         | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Python bindings for H3, a hierarchical hexagonal geospatial indexing system |
| [pybind11 cmake_example][]        | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a CMake-based build system |
| [KDEpy][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Kernel Density Estimation in Python |
| [cyvcf2][]                        | ![github icon][] | ![apple icon][] ![linux icon][] | cython + htslib == fast VCF and BCF processing |
| [pybind11 python_example][]       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Example pybind11 module built with a Python-based build system |
| [dd-trace-py][]                   | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Uses custom alternate arch emulation on GitHub |
| [sourmash][]                      | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Quickly search, compare, and analyze genomic and metagenomic data sets. |
| [time-machine][]                  | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Time mocking library using only the CPython C API. |
| [matrixprofile][]                 | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | A Python 3 library making time series data mining tasks, utilizing matrix profile algorithms, accessible to everyone. |
| [iminuit][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Jupyter-friendly Python interface for C++ MINUIT2 |
| [CTranslate2][]                   | ![github icon][] | ![apple icon][] ![linux icon][] | Includes libraries from the [Intel oneAPI toolkit](https://software.intel.com/content/www/us/en/develop/tools/oneapi/base-toolkit.html). The Linux wheels also include CUDA libraries for GPU execution. |
| [jq.py][]                         | ![travisci icon][] | ![apple icon][] ![linux icon][] | Python bindings for jq |
| [Tokenizer][]                     | ![github icon][] ![travisci icon][] | ![apple icon][] ![linux icon][] | Fast and customizable text tokenization library with BPE and SentencePiece support |
| [PyGLM][]                         | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Fast OpenGL Mathematics (GLM) for Python |
| [bx-python][]                     | ![travisci icon][] | ![apple icon][] ![linux icon][] | A library that includes Cython extensions. |
| [iDynTree][]                      | ![github icon][] | ![linux icon][] | Uses manylinux_2_24 |
| [boost-histogram][]               | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Supports full range of wheels, including PyPy and alternate archs. |
| [pybase64][]                      | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Fast Base64 encoding/decoding in Python |
| [TgCrypto][]                      | ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Includes a Windows Travis build. |
| [etebase-py][]                    | ![travisci icon][] | ![linux icon][] | Python bindings to a Rust library using `setuptools-rust`, and `sccache` for improved speed. |
| [fathon][]                        | ![travisci icon][] | ![apple icon][] ![linux icon][] | python package for DFA (Detrended Fluctuation Analysis) and related algorithms |
| [pyjet][]                         | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The interface between FastJet and NumPy |
| [numpythia][]                     | ![github icon][] | ![apple icon][] ![linux icon][] | The interface between PYTHIA and NumPy |
| [polaroid][]                      | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Full range of wheels for setuptools rust, with auto release and PyPI deploy. |
| [ninja][]                         | ![github icon][] ![travisci icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Multitagged binary builds for all supported platforms, using cibw 2 config configuration. |
| [Imagecodecs (fork)][]            | ![azurepipelines icon][] | ![apple icon][] ![linux icon][] | Over 20 external dependencies in compiled libraries, custom docker image, `libomp`, `openblas` and `install_name_tool` for macOS. |
| [GSD][]                           | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | Cython and NumPy project with 64-bit wheels. |
| [pybind11 scikit_build_example][] | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | An example combining scikit-build and pybind11 |
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
[markupsafe]: https://github.com/pallets/markupsafe
[python-snappy]: https://github.com/andrix/python-snappy
[H3-py]: https://github.com/uber/h3-py
[pybind11 cmake_example]: https://github.com/pybind/cmake_example
[KDEpy]: https://github.com/tommyod/KDEpy
[cyvcf2]: https://github.com/brentp/cyvcf2
[pybind11 python_example]: https://github.com/pybind/python_example
[dd-trace-py]: https://github.com/DataDog/dd-trace-py
[sourmash]: https://github.com/dib-lab/sourmash
[time-machine]: https://github.com/adamchainz/time-machine
[matrixprofile]: https://github.com/matrix-profile-foundation/matrixprofile
[iminuit]: https://github.com/scikit-hep/iminuit
[CTranslate2]: https://github.com/OpenNMT/CTranslate2
[jq.py]: https://github.com/mwilliamson/jq.py
[Tokenizer]: https://github.com/OpenNMT/Tokenizer
[PyGLM]: https://github.com/Zuzu-Typ/PyGLM
[bx-python]: https://github.com/bxlab/bx-python
[iDynTree]: https://github.com/robotology/idyntree
[boost-histogram]: https://github.com/scikit-hep/boost-histogram
[pybase64]: https://github.com/mayeut/pybase64
[TgCrypto]: https://github.com/pyrogram/tgcrypto
[etebase-py]: https://github.com/etesync/etebase-py
[fathon]: https://github.com/stfbnc/fathon
[pyjet]: https://github.com/scikit-hep/pyjet
[numpythia]: https://github.com/scikit-hep/numpythia
[polaroid]: https://github.com/daggy1234/polaroid
[ninja]: https://github.com/scikit-build/ninja-python-distributions
[Imagecodecs (fork)]: https://github.com/czaki/imagecodecs_build
[GSD]: https://github.com/glotzerlab/gsd
[pybind11 scikit_build_example]: https://github.com/pybind/scikit_build_example
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

<!-- scikit-learn: 46722, last pushed 0 days ago -->
<!-- Matplotlib: 14010, last pushed 0 days ago -->
<!-- MyPy: 11113, last pushed 0 days ago -->
<!-- psutil: 7535, last pushed 1 days ago -->
<!-- scikit-image: 4444, last pushed 0 days ago -->
<!-- twisted-iocpsupport: 4322, last pushed 0 days ago -->
<!-- cmake: 4050, last pushed 0 days ago -->
<!-- websockets: 3490, last pushed 7 days ago -->
<!-- pyzmq: 2866, last pushed 2 days ago -->
<!-- aiortc: 2500, last pushed 27 days ago -->
<!-- River: 1828, last pushed 3 days ago -->
<!-- coverage.py: 1667, last pushed 0 days ago -->
<!-- numexpr: 1615, last pushed 30 days ago -->
<!-- h5py: 1554, last pushed 2 days ago -->
<!-- Dependency Injector: 1493, last pushed 0 days ago -->
<!-- PyAV: 1309, last pushed 61 days ago -->
<!-- PyTables: 1047, last pushed 18 days ago -->
<!-- ruptures: 768, last pushed 3 days ago -->
<!-- aioquic: 720, last pushed 12 days ago -->
<!-- pikepdf: 706, last pushed 4 days ago -->
<!-- google neuroglancer: 671, last pushed 1 days ago -->
<!-- DeepForest: 638, last pushed 14 days ago -->
<!-- AutoPy: 561, last pushed 50 days ago -->
<!-- Parselmouth: 536, last pushed 0 days ago -->
<!-- python-rapidjson: 424, last pushed 42 days ago -->
<!-- Rtree: 415, last pushed 139 days ago -->
<!-- markupsafe: 411, last pushed 1 days ago -->
<!-- python-snappy: 407, last pushed 16 days ago -->
<!-- H3-py: 407, last pushed 55 days ago -->
<!-- pybind11 cmake_example: 296, last pushed 1 days ago -->
<!-- KDEpy: 287, last pushed 64 days ago -->
<!-- cyvcf2: 267, last pushed 10 days ago -->
<!-- pybind11 python_example: 259, last pushed 1 days ago -->
<!-- dd-trace-py: 259, last pushed 0 days ago -->
<!-- sourmash: 258, last pushed 0 days ago -->
<!-- time-machine: 189, last pushed 1 days ago -->
<!-- matrixprofile: 187, last pushed 42 days ago -->
<!-- iminuit: 182, last pushed 1 days ago -->
<!-- CTranslate2: 177, last pushed 0 days ago -->
<!-- jq.py: 167, last pushed 4 days ago -->
<!-- Tokenizer: 150, last pushed 1 days ago -->
<!-- PyGLM: 107, last pushed 17 days ago -->
<!-- bx-python: 105, last pushed 29 days ago -->
<!-- iDynTree: 85, last pushed 4 days ago -->
<!-- boost-histogram: 83, last pushed 4 days ago -->
<!-- pybase64: 72, last pushed 3 days ago -->
<!-- TgCrypto: 68, last pushed 68 days ago -->
<!-- etebase-py: 51, last pushed 214 days ago -->
<!-- fathon: 33, last pushed 65 days ago -->
<!-- pyjet: 30, last pushed 79 days ago -->
<!-- numpythia: 30, last pushed 12 days ago -->
<!-- polaroid: 22, last pushed 12 days ago -->
<!-- ninja: 19, last pushed 1 days ago -->
<!-- Imagecodecs (fork): 17, last pushed 6 days ago -->
<!-- GSD: 17, last pushed 5 days ago -->
<!-- pybind11 scikit_build_example: 16, last pushed 3 days ago -->
<!-- pyinstrument_cext: 10, last pushed 22 days ago -->
<!-- xmlstarlet: 7, last pushed 15 days ago -->
<!-- CorrectionLib: 6, last pushed 10 days ago -->
<!-- SiPM: 4, last pushed 28 days ago -->

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

<!--changelog-start-->

### v2.1.1

_7 August 2021_

- ✨ Corresponding with the release of CPython 3.10.0rc1, which is ABI stable, cibuildwheel now builds CPython 3.10 by default - without the CIBW_PRERELEASE_PYTHONS flag.

<sup>Note: v2.1.0 was a bad release, it was yanked from PyPI.</sup>

### v2.0.1

_25 July 2021_

- 📚 Docs improvements (#767)
- 🛠 Dependency updates, including delocate 0.9.0.

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

### v1.9.0

_5 February 2021_

- 🌟 Added support for Apple Silicon wheels on macOS! You can now
  cross-compile `universal2` and `arm64` wheels on your existing macOS Intel
  runners, by setting
  [CIBW_ARCHS_MACOS](https://cibuildwheel.readthedocs.io/en/stable/options/#archs).
  Xcode 12.2 or later is required, but you don't need macOS 11.0 - you can
  still build on macOS 10.15. See
  [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#apple-silicon)
  for more information. (#484)
- 🌟 Added auto-detection of your package's Python compatibility, via declared
   [`requires-python`](https://www.python.org/dev/peps/pep-0621/#requires-python)
  in your `pyproject.toml`, or
  [`python_requires`](https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires)
  in `setup.cfg` or `setup.py`. If your project has these set, cibuildwheel
  will automatically skip builds on versions of Python that your package
  doesn't support. Hopefully this makes the first-run experience of
  cibuildwheel a bit easier. If you need to override this for any reason,
  look at [`CIBW_PROJECT_REQUIRES_PYTHON`](https://cibuildwheel.readthedocs.io/en/stable/options/#requires-python).
  (#536)
- 🌟 cibuildwheel can now be invoked as a native GitHub Action! You can now
  invoke cibuildwheel in a GHA build step like:

  ```yaml
  - name: Build wheels
    uses: pypa/cibuildwheel@version # e.g. v1.9.0
    with:
      output-dir: wheelhouse
    # env:
    #   CIBW_SOME_OPTION: value
  ```

  This saves a bit of boilerplate, and you can [use Dependabot to keep the
  pinned version up-to-date](https://cibuildwheel.readthedocs.io/en/stable/faq/#automatic-updates).

- ✨ Added `auto64` and `auto32` shortcuts to the
  [CIBW_ARCHS](https://cibuildwheel.readthedocs.io/en/stable/options/#archs)
  option. (#553)
- ✨ cibuildwheel now prints a list of the wheels built at the end of each
  run. (#570)
- 📚 Lots of minor docs improvements.

### 1.8.0

_22 January 2021_

- 🌟 Added support for emulated builds! You can now build manylinux wheels on
  ARM64`aarch64`, as well as `ppc64le` and 's390x'. To build under emulation,
  register QEMU via binfmt_misc and set the
  [`CIBW_ARCHS_LINUX`](https://cibuildwheel.readthedocs.io/en/stable/options/#archs)
  option to the architectures you want to run. See
  [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#emulation)
  for more information. (#482)
- ✨ Added `CIBW_TEST_SKIP` option. This allows you to choose certain builds
  whose tests you'd like to skip. This might be useful when running a slow
  test suite under emulation, for example. (#537)
- ✨ Added `curly-{brace,bracket,paren}` style globbing to `CIBW_BUILD` and
  `CIBW_SKIP`. This gives more expressivity, letting you do things like
  `CIBW_BUILD=cp39-manylinux_{aarch64,ppc64le}`. (#527)
- 🛠 cibuildwheel will now exit with an error if it's called with options that
  skip all builds on a platform. This feature can be disabled by adding
  `--allow-empty` on the command line. (#545)

### 1.7.4

_2 January 2021_

- 🐛 Fix the PyPy virtualenv patch to work on macOS 10.14 (#506)

### 1.7.3

_1 January 2021_

- 🛠 Added a patch for Pypy to ensure header files are available for building
  in a virtualenv. (#502)
- 🛠 Some preparatory work towards using cibuildwheel as a GitHub Action.
  Check out
  [the FAQ](https://cibuildwheel.readthedocs.io/en/stable/faq/#option-1-github-action)
  for information on how to use it. We'll be fully updating the docs to this
  approach in a subsequent release (#494)

### 1.7.2

_21 December 2020_

- 🛠 Update dependencies, notably wheel==0.36.2 and pip==20.3.3, and CPython to
  their latest bugfix releases (#489)
- 📚 Switch to a GitHub example in the README (#479)
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
  disk drive" on GitHub Actions (#388, #389)

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
- 📚 Improved GitHub Actions examples and docs (#354, #362)
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

- 🌟 Add support for building on GitHub Actions! Check out the
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
  [cibuildwheel-azure-example](https://github.com/pypa/cibuildwheel-azure-example)
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
