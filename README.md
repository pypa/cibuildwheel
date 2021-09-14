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
| CPython 3.10  | ✅ | ✅  | ✅  | ✅  | ✅ | ✅  | ✅ | ✅  | ✅  |
| PyPy 3.7 v7.3 | ✅ | N/A | ✅  | N/A | ✅ | ✅  | ✅ | N/A | N/A |


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
        run: python -m pip install cibuildwheel==2.1.2

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
|   | [`CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons)  | Enable building with pre-release versions of Python if available |
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

[appveyor icon]: docs/data/readme_icons/appveyor.svg
[github icon]: docs/data/readme_icons/github.svg
[azurepipelines icon]: docs/data/readme_icons/azurepipelines.svg
[circleci icon]: docs/data/readme_icons/circleci.svg
[gitlab icon]: docs/data/readme_icons/gitlab.svg
[travisci icon]: docs/data/readme_icons/travisci.svg
[windows icon]: docs/data/readme_icons/windows.svg
[apple icon]: docs/data/readme_icons/apple.svg
[linux icon]: docs/data/readme_icons/linux.svg

<!-- END bin/projects.py -->

> ℹ️ That's just a handful, there are many more! Check out the [Working Examples](https://cibuildwheel.readthedocs.io/en/stable/working-examples) page in the docs.

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

<!-- START bin/update_readme_changelog.py -->

<!-- this section was generated by bin/update_readme_changelog.py -- do not edit manually -->

### v2.1.2

_14 September 2021_

- 🛠 Updated CPython 3.10 to 3.10.0rc2
- 📚 Multiple docs updates
- 🐛 Improved warnings when built binaries are bundled into the container on Linux. (#807)

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
