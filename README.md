cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel)
[![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.pypa.io/en/stable/?badge=stable)
[![Actions Status](https://github.com/pypa/cibuildwheel/workflows/Test/badge.svg)](https://github.com/pypa/cibuildwheel/actions)
[![Travis Status](https://img.shields.io/travis/com/pypa/cibuildwheel/main?logo=travis)](https://travis-ci.com/github/pypa/cibuildwheel)
[![Appveyor status](https://ci.appveyor.com/api/projects/status/gt3vwl88yt0y3hur/branch/main?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/main)
[![CircleCI Status](https://img.shields.io/circleci/build/gh/pypa/cibuildwheel/main?logo=circleci)](https://circleci.com/gh/pypa/cibuildwheel)
[![Azure Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/pypa.cibuildwheel?branchName=main)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=4&branchName=main)


[Documentation](https://cibuildwheel.pypa.io)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, and GitLab CI - and it builds and tests your wheels across all of your platforms.


What does it do?
----------------

While cibuildwheel itself requires a recent Python version to run (we support the last three releases), it can target the following versions to build wheels:

|                | macOS Intel | macOS Apple Silicon | Windows 64bit | Windows 32bit | Windows Arm64 | manylinux<br/>musllinux x86_64 | manylinux<br/>musllinux i686 | manylinux<br/>musllinux aarch64 | manylinux<br/>musllinux ppc64le | manylinux<br/>musllinux s390x | manylinux<br/>musllinux armv7l | Pyodide |
|----------------|----|-----|-----|-----|-----|----|-----|----|-----|-----|---|-----|
| CPython 3.6    | ✅ | N/A | ✅  | ✅  | N/A | ✅  | ✅  | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.7    | ✅ | N/A | ✅  | ✅  | N/A | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.8    | ✅ | ✅  | ✅  | ✅  | N/A | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.9    | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅ | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.10   | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.11   | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵ | N/A |
| CPython 3.12   | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵  | ✅⁴ |
| CPython 3.13³  | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  | ✅⁵  | N/A |
| PyPy 3.7 v7.3  | ✅ | N/A | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A | N/A | N/A |
| PyPy 3.8 v7.3  | ✅ | ✅  | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A | N/A | N/A |
| PyPy 3.9 v7.3  | ✅ | ✅  | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A | N/A | N/A |
| PyPy 3.10 v7.3 | ✅ | ✅  | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A | N/A | N/A |
| PyPy 3.11 v7.3 | ✅ | ✅  | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A | N/A | N/A |

<sup>¹ PyPy is only supported for manylinux wheels.</sup><br>
<sup>² Windows arm64 support is experimental.</sup><br>
<sup>³ Free-threaded mode requires opt-in using [`CIBW_FREE_THREADED_SUPPORT`](https://cibuildwheel.pypa.io/en/stable/options/#free-threaded-support).</sup><br>
<sup>⁴ Experimental, not yet supported on PyPI, but can be used directly in web deployment. Use `--platform pyodide` to build.</sup><br>
<sup>⁵ manylinux armv7l support is experimental. As there are no RHEL based image for this architecture, it's using an Ubuntu based image instead.</sup><br>

- Builds manylinux, musllinux, macOS 10.9+ (10.13+ for Python 3.12+), and Windows wheels for CPython and PyPy
- Works on GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, GitLab CI, and Cirrus CI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs your library's tests against the wheel-installed version of your library

See the [cibuildwheel 1 documentation](https://cibuildwheel.pypa.io/en/1.x/) if you need to build unsupported versions of Python, such as Python 2.

Usage
-----

`cibuildwheel` runs inside a CI service. Supported platforms depend on which service you're using:

|                 | Linux | macOS | Windows | Linux ARM | macOS ARM | Windows ARM |
|-----------------|-------|-------|---------|-----------|-----------|-------------|
| GitHub Actions  | ✅    | ✅    | ✅       | ✅        | ✅        | ✅²         |
| Azure Pipelines | ✅    | ✅    | ✅       |           | ✅        | ✅²         |
| Travis CI       | ✅    |       | ✅      | ✅        |           |             |
| AppVeyor        | ✅    | ✅    | ✅      |           | ✅        | ✅²         |
| CircleCI        | ✅    | ✅    |         | ✅        | ✅        |             |
| Gitlab CI       | ✅    | ✅    | ✅      | ✅¹       | ✅        |             |
| Cirrus CI       | ✅    | ✅    | ✅      | ✅        | ✅        |             |

<sup>¹ [Requires emulation](https://cibuildwheel.pypa.io/en/stable/faq/#emulation), distributed separately. Other services may also support Linux ARM through emulation or third-party build hosts, but these are not tested in our CI.</sup><br>
<sup>² [Uses cross-compilation](https://cibuildwheel.pypa.io/en/stable/faq/#windows-arm64). It is not possible to test `arm64` on this CI platform.</sup>

<!--intro-end-->

Example setup
-------------

To build manylinux, musllinux, macOS, and Windows wheels on GitHub Actions, you could use this `.github/workflows/wheels.yml`:

```yaml
name: Build

on: [push, pull_request]

jobs:
  build_wheels:
    name: Build wheels on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, ubuntu-24.04-arm, windows-latest, macos-13, macos-latest]

    steps:
      - uses: actions/checkout@v4

      # Used to host cibuildwheel
      - uses: actions/setup-python@v5

      - name: Install cibuildwheel
        run: python -m pip install cibuildwheel==2.23.3

      - name: Build wheels
        run: python -m cibuildwheel --output-dir wheelhouse
        # to supply options, put them in 'env', like:
        # env:
        #   CIBW_SOME_OPTION: value

      - uses: actions/upload-artifact@v4
        with:
          name: cibw-wheels-${{ matrix.os }}-${{ strategy.job-index }}
          path: ./wheelhouse/*.whl
```

For more information, including PyPI deployment, and the use of other CI services or the dedicated GitHub Action, check out the [documentation](https://cibuildwheel.pypa.io) and the [examples](https://github.com/pypa/cibuildwheel/tree/main/examples).

How it works
------------

The following diagram summarises the steps that cibuildwheel takes on each platform.

![](docs/data/how-it-works.png)

<sup>Explore an interactive version of this diagram [in the docs](https://cibuildwheel.pypa.io/en/stable/#how-it-works).</sup>

Options
-------

|   | Option | Description |
|---|--------|-------------|
| **Build selection** | [`CIBW_PLATFORM`](https://cibuildwheel.pypa.io/en/stable/options/#platform)  | Override the auto-detected target platform |
|   | [`CIBW_BUILD`](https://cibuildwheel.pypa.io/en/stable/options/#build-skip)  <br> [`CIBW_SKIP`](https://cibuildwheel.pypa.io/en/stable/options/#build-skip)  | Choose the Python versions to build |
|   | [`CIBW_ARCHS`](https://cibuildwheel.pypa.io/en/stable/options/#archs)  | Change the architectures built on your machine by default. |
|   | [`CIBW_PROJECT_REQUIRES_PYTHON`](https://cibuildwheel.pypa.io/en/stable/options/#requires-python)  | Manually set the Python compatibility of your project |
|   | [`CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.pypa.io/en/stable/options/#prerelease-pythons)  | Enable building with pre-release versions of Python if available |
| **Build customization** | [`CIBW_BUILD_FRONTEND`](https://cibuildwheel.pypa.io/en/stable/options/#build-frontend)  | Set the tool to use to build, either "pip" (default for now) or "build" |
|   | [`CIBW_ENVIRONMENT`](https://cibuildwheel.pypa.io/en/stable/options/#environment)  | Set environment variables needed during the build |
|   | [`CIBW_ENVIRONMENT_PASS_LINUX`](https://cibuildwheel.pypa.io/en/stable/options/#environment-pass)  | Set environment variables on the host to pass-through to the container during the build. |
|   | [`CIBW_BEFORE_ALL`](https://cibuildwheel.pypa.io/en/stable/options/#before-all)  | Execute a shell command on the build system before any wheels are built. |
|   | [`CIBW_BEFORE_BUILD`](https://cibuildwheel.pypa.io/en/stable/options/#before-build)  | Execute a shell command preparing each wheel's build |
|   | [`CIBW_REPAIR_WHEEL_COMMAND`](https://cibuildwheel.pypa.io/en/stable/options/#repair-wheel-command)  | Execute a shell command to repair each built wheel |
|   | [`CIBW_MANYLINUX_*_IMAGE`<br/>`CIBW_MUSLLINUX_*_IMAGE`](https://cibuildwheel.pypa.io/en/stable/options/#linux-image)  | Specify alternative manylinux / musllinux Docker images |
|   | [`CIBW_CONTAINER_ENGINE`](https://cibuildwheel.pypa.io/en/stable/options/#container-engine)  | Specify which container engine to use when building Linux wheels |
|   | [`CIBW_DEPENDENCY_VERSIONS`](https://cibuildwheel.pypa.io/en/stable/options/#dependency-versions)  | Specify how cibuildwheel controls the versions of the tools it uses |
| **Testing** | [`CIBW_TEST_COMMAND`](https://cibuildwheel.pypa.io/en/stable/options/#test-command)  | Execute a shell command to test each built wheel |
|   | [`CIBW_BEFORE_TEST`](https://cibuildwheel.pypa.io/en/stable/options/#before-test)  | Execute a shell command before testing each wheel |
|   | [`CIBW_TEST_REQUIRES`](https://cibuildwheel.pypa.io/en/stable/options/#test-requires)  | Install Python dependencies before running the tests |
|   | [`CIBW_TEST_EXTRAS`](https://cibuildwheel.pypa.io/en/stable/options/#test-extras)  | Install your wheel for testing using extras_require |
|   | [`CIBW_TEST_SKIP`](https://cibuildwheel.pypa.io/en/stable/options/#test-skip)  | Skip running tests on some builds |
| **Other** | [`CIBW_BUILD_VERBOSITY`](https://cibuildwheel.pypa.io/en/stable/options/#build-verbosity)  | Increase/decrease the output of pip wheel |

These options can be specified in a pyproject.toml file, as well; see [configuration](https://cibuildwheel.pypa.io/en/stable/options/#configuration).

Working examples
----------------

Here are some repos that use cibuildwheel.

<!-- START bin/projects.py -->

<!-- this section is generated by bin/projects.py. Don't edit it directly, instead, edit docs/data/projects.yml -->

| Name                              | CI | OS | Notes |
|-----------------------------------|----|----|:------|
| [scikit-learn][]                  | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The machine learning library. A complex but clean config using many of cibuildwheel's features to build a large project with Cython and C++ extensions.  |
| [pytorch-fairseq][]               | ![github icon][] | ![apple icon][] ![linux icon][] | Facebook AI Research Sequence-to-Sequence Toolkit written in Python. |
| [NumPy][]                         | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The fundamental package for scientific computing with Python. |
| [duckdb][]                        | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | DuckDB is an analytical in-process SQL database management system |
| [Tornado][]                       | ![github icon][] | ![linux icon][] ![apple icon][] ![windows icon][] | Tornado is a Python web framework and asynchronous networking library. Uses stable ABI for a small C extension. |
| [NCNN][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | ncnn is a high-performance neural network inference framework optimized for the mobile platform |
| [Matplotlib][]                    | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The venerable Matplotlib, a Python library with C++ portions |
| [Prophet][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Tool for producing high quality forecasts for time series data that has multiple seasonality with linear or non-linear growth. |
| [MyPy][]                          | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | The compiled version of MyPy using MyPyC. |
| [Kivy][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Open source UI framework written in Python, running on Windows, Linux, macOS, Android and iOS |

[scikit-learn]: https://github.com/scikit-learn/scikit-learn
[pytorch-fairseq]: https://github.com/facebookresearch/fairseq
[NumPy]: https://github.com/numpy/numpy
[duckdb]: https://github.com/duckdb/duckdb
[Tornado]: https://github.com/tornadoweb/tornado
[NCNN]: https://github.com/Tencent/ncnn
[Matplotlib]: https://github.com/matplotlib/matplotlib
[Prophet]: https://github.com/facebook/prophet
[MyPy]: https://github.com/mypyc/mypy_mypyc-wheels
[Kivy]: https://github.com/kivy/kivy

[appveyor icon]: docs/data/readme_icons/appveyor.svg
[github icon]: docs/data/readme_icons/github.svg
[azurepipelines icon]: docs/data/readme_icons/azurepipelines.svg
[circleci icon]: docs/data/readme_icons/circleci.svg
[gitlab icon]: docs/data/readme_icons/gitlab.svg
[travisci icon]: docs/data/readme_icons/travisci.svg
[cirrusci icon]: docs/data/readme_icons/cirrusci.svg
[windows icon]: docs/data/readme_icons/windows.svg
[apple icon]: docs/data/readme_icons/apple.svg
[linux icon]: docs/data/readme_icons/linux.svg

<!-- END bin/projects.py -->

> ℹ️ That's just a handful, there are many more! Check out the [Working Examples](https://cibuildwheel.pypa.io/en/stable/working-examples) page in the docs.

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some license implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

<!-- START bin/update_readme_changelog.py -->

<!-- this section was generated by bin/update_readme_changelog.py -- do not edit manually -->

### v2.23.3

_26 April 2025_

- 🛠 Dependency updates, including Python 3.13.3 (#2371)

### v2.23.2

_24 March 2025_

- 🐛 Workaround an issue with pyodide builds when running cibuildwheel with a Python that was installed via UV (#2328 via #2331)
- 🛠 Dependency updates, including a manylinux update that fixes an ['undefined symbol' error](https://github.com/pypa/manylinux/issues/1760) in gcc-toolset (#2334)

### v2.23.1

_15 March 2025_

- ⚠️ Added warnings when the shorthand values `manylinux1`, `manylinux2010`, `manylinux_2_24`, and `musllinux_1_1` are used to specify the images in linux builds. The shorthand to these (unmaintainted) images will be removed in v3.0. If you want to keep using these images, explicitly opt-in using the full image URL, which can be found in [this file](https://github.com/pypa/cibuildwheel/blob/v2.23.1/cibuildwheel/resources/pinned_docker_images.cfg). (#2312)
- 🛠 Dependency updates, including a manylinux update which fixes an [issue with rustup](https://github.com/pypa/cibuildwheel/issues/2303). (#2315)

### v2.23.0

_1 March 2025_

- ✨ Adds official support for the new GitHub Actions Arm runners. In fact these worked out-of-the-box, now we include them in our tests and example configs. (#2135 via #2281)
- ✨ Adds support for building PyPy 3.11 wheels (#2268 via #2281)
- 🛠 Adopts the beta pypa/manylinux image for armv7l builds (#2269 via #2281)
- 🛠 Dependency updates, including Pyodide 0.27 (#2117 and #2281)

### v2.22.0

_23 November 2024_

- 🌟 Added a new `CIBW_ENABLE`/`enable` feature that replaces `CIBW_FREETHREADED_SUPPORT`/`free-threaded-support` and `CIBW_PRERELEASE_PYTHONS` with a system that supports both. In cibuildwheel 3, this will also include a PyPy setting and the deprecated options will be removed. (#2048)
- 🌟 [Dependency groups](https://peps.python.org/pep-0735/) are now supported for tests. Use `CIBW_TEST_GROUPS`/`test-groups` to specify groups in `[dependency-groups]` for testing. (#2063)
- 🌟 Support for the experimental Ubuntu-based ARMv7l manylinux image (#2052)
- ✨ Show a warning when cibuildwheel is run from Python 3.10 or older; cibuildwheel 3.0 will require Python 3.11 or newer as host (#2050)
- 🐛 Fix issue with stderr interfering with checking the docker version (#2074)
- 🛠 Python 3.9 is now used in `CIBW_BEFORE_ALL`/`before-all` on linux, replacing 3.8, which is now EoL (#2043)
- 🛠 Error messages for producing a pure-Python wheel are slightly more informative (#2044)
- 🛠 Better error when `uname -m` fails on ARM (#2049)
- 🛠 Better error when repair fails and docs for abi3audit on Windows (#2058)
- 🛠 Better error when `manylinux-interpreters ensure` fails (#2066)
- 🛠 Update Pyodide to 0.26.4, and adapt to the unbundled pyodide-build (now 0.29) (#2090)
- 🛠 Now cibuildwheel uses dependency-groups for development dependencies (#2064, #2085)
- 📚 Docs updates and tidy ups (#2061, #2067, #2072)

<!-- END bin/update_readme_changelog.py -->

---

That's the last few versions.

ℹ️ **Want more changelog? Head over to [the changelog page in the docs](https://cibuildwheel.pypa.io/en/stable/changelog/).**

---

Contributing
============

For more info on how to contribute to cibuildwheel, see the [docs](https://cibuildwheel.pypa.io/en/latest/contributing/).

Everyone interacting with the cibuildwheel project via codebase, issue tracker, chat rooms, or otherwise is expected to follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).

Maintainers
-----------

- Joe Rickerby [@joerick](https://github.com/joerick)
- Yannick Jadoul [@YannickJadoul](https://github.com/YannickJadoul)
- Matthieu Darbois [@mayeut](https://github.com/mayeut)
- Henry Schreiner [@henryiii](https://github.com/henryiii)
- Grzegorz Bokota [@Czaki](https://github.com/Czaki)

Credits
-------

`cibuildwheel` stands on the shoulders of giants.

- ⭐️ @matthew-brett for [multibuild](https://github.com/multi-build/multibuild) and [matthew-brett/delocate](http://github.com/matthew-brett/delocate)
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

Another very similar tool to consider is [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a shell script toolbox for building a wheel on various platforms. It is used as a basis to build some of the big data science tools, like SciPy.

If you are building Rust wheels, you can get by without some of the tricks required to make GLIBC work via manylinux; this is especially relevant for cross-compiling, which is easy with Rust. See [maturin-action](https://github.com/PyO3/maturin-action) for a tool that is optimized for building Rust wheels and cross-compiling.
