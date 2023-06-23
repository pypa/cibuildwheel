cibuildwheel
============

[![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel)
[![Documentation Status](https://readthedocs.org/projects/cibuildwheel/badge/?version=stable)](https://cibuildwheel.readthedocs.io/en/stable/?badge=stable)
[![Actions Status](https://github.com/pypa/cibuildwheel/workflows/Test/badge.svg)](https://github.com/pypa/cibuildwheel/actions)
[![Travis Status](https://img.shields.io/travis/com/pypa/cibuildwheel/main?logo=travis)](https://travis-ci.com/pypa/cibuildwheel)
[![Appveyor status](https://ci.appveyor.com/api/projects/status/gt3vwl88yt0y3hur/branch/main?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/main)
[![CircleCI Status](https://img.shields.io/circleci/build/gh/pypa/cibuildwheel/main?logo=circleci)](https://circleci.com/gh/pypa/cibuildwheel)
[![Azure Status](https://dev.azure.com/joerick0429/cibuildwheel/_apis/build/status/pypa.cibuildwheel?branchName=main)](https://dev.azure.com/joerick0429/cibuildwheel/_build/latest?definitionId=4&branchName=main)
[![Cirrus CI Status](https://img.shields.io/cirrus/github/pypa/cibuildwheel/main?logo=cirrusci)](https://cirrus-ci.com/github/pypa/cibuildwheel)


[Documentation](https://cibuildwheel.readthedocs.org)

<!--intro-start-->

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, and GitLab CI - and it builds and tests your wheels across all of your platforms.


What does it do?
----------------

|   | macOS Intel | macOS Apple Silicon | Windows 64bit | Windows 32bit | Windows Arm64 | manylinux<br/>musllinux x86_64 | manylinux<br/>musllinux i686 | manylinux<br/>musllinux aarch64 | manylinux<br/>musllinux ppc64le | manylinux<br/>musllinux s390x |
|----------------|----|-----|-----|-----|-----|----|-----|----|-----|-----|
| CPython 3.6    | ✅ | N/A | ✅  | ✅  | N/A | ✅  | ✅  | ✅ | ✅  | ✅  |
| CPython 3.7    | ✅ | N/A | ✅  | ✅  | N/A | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.8    | ✅ | ✅  | ✅  | ✅  | N/A | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.9    | ✅ | ✅  | ✅  | ✅  | ✅² | ✅³ | ✅ | ✅ | ✅  | ✅  |
| CPython 3.10   | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.11   | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  |
| CPython 3.12⁵  | ✅ | ✅  | ✅  | ✅  | ✅² | ✅ | ✅  | ✅ | ✅  | ✅  |
| PyPy 3.7 v7.3  | ✅ | N/A | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A |
| PyPy 3.8 v7.3  | ✅ | ✅⁴ | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A |
| PyPy 3.9 v7.3  | ✅ | ✅⁴ | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A |
| PyPy 3.10 v7.3 | ✅ | ✅⁴ | ✅  | N/A | N/A | ✅¹ | ✅¹  | ✅¹ | N/A | N/A |

<sup>¹ PyPy is only supported for manylinux wheels.</sup><br>
<sup>² Windows arm64 support is experimental.</sup><br>
<sup>³ Alpine 3.14 and very briefly 3.15's default python3 [was not able to load](https://github.com/pypa/cibuildwheel/issues/934) musllinux wheels. This has been fixed; please upgrade the python package if using Alpine from before the fix.</sup><br>
<sup>⁴ Cross-compilation not supported with PyPy - to build these wheels you need to run cibuildwheel on an Apple Silicon machine.</sup><br>
<sup>⁵ CPython 3.12 is available using the [CIBW_PRERELEASE_PYTHONS](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons) option.</sup><br>

- Builds manylinux, musllinux, macOS 10.9+, and Windows wheels for CPython and PyPy
- Works on GitHub Actions, Azure Pipelines, Travis CI, AppVeyor, CircleCI, GitLab CI, and Cirrus CI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs your library's tests against the wheel-installed version of your library

See the [cibuildwheel 1 documentation](https://cibuildwheel.readthedocs.io/en/1.x/) if you need to build unsupported versions of Python, such as Python 2.

Usage
-----

`cibuildwheel` runs inside a CI service. Supported platforms depend on which service you're using:

|                 | Linux | macOS | Windows | Linux ARM | macOS ARM | Windows ARM |
|-----------------|-------|-------|---------|-----------|-----------|-------------|
| GitHub Actions  | ✅    | ✅    | ✅      | ✅¹       | ✅²       | ✅⁴         |
| Azure Pipelines | ✅    | ✅    | ✅      |           | ✅²       | ✅⁴         |
| Travis CI       | ✅    |       | ✅      | ✅        |           |             |
| AppVeyor        | ✅    | ✅    | ✅      |           | ✅²       | ✅⁴         |
| CircleCI        | ✅    | ✅    |         | ✅        | ✅²       |             |
| Gitlab CI       | ✅    |       | ✅      | ✅¹       |           |             |
| Cirrus CI       | ✅    | ✅³   | ✅      | ✅        | ✅        |             |

<sup>¹ [Requires emulation](https://cibuildwheel.readthedocs.io/en/stable/faq/#emulation), distributed separately. Other services may also support Linux ARM through emulation or third-party build hosts, but these are not tested in our CI.</sup><br>
<sup>² [Uses cross-compilation](https://cibuildwheel.readthedocs.io/en/stable/faq/#universal2). It is not possible to test `arm64` and the `arm64` part of a `universal2` wheel on this CI platform.</sup><br>
<sup>³ [Uses cross-compilation](https://cibuildwheel.readthedocs.io/en/stable/faq/#universal2). Thanks to Rosetta 2 emulation, it is possible to test `x86_64` and both parts of a `universal2` wheel on this CI platform.</sup><br>
<sup>⁴ [Uses cross-compilation](https://cibuildwheel.readthedocs.io/en/stable/faq/#windows-arm64). It is not possible to test `arm64` on this CI platform.</sup>

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
        os: [ubuntu-20.04, windows-2019, macOS-11]

    steps:
      - uses: actions/checkout@v3

      # Used to host cibuildwheel
      - uses: actions/setup-python@v3

      - name: Install cibuildwheel
        run: python -m pip install cibuildwheel==2.13.1

      - name: Build wheels
        run: python -m cibuildwheel --output-dir wheelhouse
        # to supply options, put them in 'env', like:
        # env:
        #   CIBW_SOME_OPTION: value

      - uses: actions/upload-artifact@v3
        with:
          path: ./wheelhouse/*.whl
```

For more information, including PyPI deployment, and the use of other CI services or the dedicated GitHub Action, check out the [documentation](https://cibuildwheel.readthedocs.org) and the [examples](https://github.com/pypa/cibuildwheel/tree/main/examples).

How it works
------------

The following diagram summarises the steps that cibuildwheel takes on each platform.

![](docs/data/how-it-works.png)

<sup>Explore an interactive version of this diagram [in the docs](https://cibuildwheel.readthedocs.io/en/stable/#how-it-works).</sup>

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
|   | [`CIBW_ENVIRONMENT_PASS_LINUX`](https://cibuildwheel.readthedocs.io/en/stable/options/#environment-pass)  | Set environment variables on the host to pass-through to the container during the build. |
|   | [`CIBW_BEFORE_ALL`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-all)  | Execute a shell command on the build system before any wheels are built. |
|   | [`CIBW_BEFORE_BUILD`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-build)  | Execute a shell command preparing each wheel's build |
|   | [`CIBW_REPAIR_WHEEL_COMMAND`](https://cibuildwheel.readthedocs.io/en/stable/options/#repair-wheel-command)  | Execute a shell command to repair each built wheel |
|   | [`CIBW_MANYLINUX_*_IMAGE`<br/>`CIBW_MUSLLINUX_*_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image)  | Specify alternative manylinux / musllinux Docker images |
|   | [`CIBW_CONTAINER_ENGINE`](https://cibuildwheel.readthedocs.io/en/stable/options/#container-engine)  | Specify which container engine to use when building Linux wheels |
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
| [pytorch-fairseq][]               | ![github icon][] | ![apple icon][] ![linux icon][] | Facebook AI Research Sequence-to-Sequence Toolkit written in Python. |
| [NumPy][]                         | ![github icon][] ![travisci icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The fundamental package for scientific computing with Python. |
| [Tornado][]                       | ![travisci icon][] | ![apple icon][] ![linux icon][] | Tornado is a Python web framework and asynchronous networking library, originally developed at FriendFeed. |
| [Matplotlib][]                    | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | The venerable Matplotlib, a Python library with C++ portions |
| [NCNN][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | ncnn is a high-performance neural network inference framework optimized for the mobile platform |
| [Prophet][]                       | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Tool for producing high quality forecasts for time series data that has multiple seasonality with linear or non-linear growth. |
| [Kivy][]                          | ![github icon][] | ![windows icon][] ![apple icon][] ![linux icon][] | Open source UI framework written in Python, running on Windows, Linux, macOS, Android and iOS |
| [MyPy][]                          | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | The compiled version of MyPy using MyPyC. |
| [duckdb][]                        | ![github icon][] | ![apple icon][] ![linux icon][] ![windows icon][] | DuckDB is an in-process SQL OLAP Database Management System |

[scikit-learn]: https://github.com/scikit-learn/scikit-learn
[pytorch-fairseq]: https://github.com/pytorch/fairseq
[NumPy]: https://github.com/numpy/numpy
[Tornado]: https://github.com/tornadoweb/tornado
[Matplotlib]: https://github.com/matplotlib/matplotlib
[NCNN]: https://github.com/Tencent/ncnn
[Prophet]: https://github.com/facebook/prophet
[Kivy]: https://github.com/kivy/kivy
[MyPy]: https://github.com/mypyc/mypy_mypyc-wheels
[duckdb]: https://github.com/duckdb/duckdb

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

> ℹ️ That's just a handful, there are many more! Check out the [Working Examples](https://cibuildwheel.readthedocs.io/en/stable/working-examples) page in the docs.

Legal note
----------

Since `cibuildwheel` repairs the wheel with `delocate` or `auditwheel`, it might automatically bundle dynamically linked libraries from the build machine.

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some license implications. Check the license for any code you're pulling in to make sure that's allowed.

Changelog
=========

<!-- START bin/update_readme_changelog.py -->

<!-- this section was generated by bin/update_readme_changelog.py -- do not edit manually -->

### v2.13.1

_10 June 2023_

- 🛠 Updates the prerelease CPython 3.12 version to 3.12.0b2. (#1516)
- 🛠 Adds a moving `v<major>.<minor>` tag for use in GitHub Actions workflow files. If you use this, you'll get the latest patch release within a minor version. Additionally, Dependabot won't send you PRs for patch releases. (#1517)

### v2.13.0

_28 May 2023_

- ✨ Adds CPython 3.12 support, under the prerelease flag [CIBW_PRERELEASE_PYTHONS](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons). This version of cibuildwheel uses 3.12.0b1.

    While CPython is in beta, the ABI can change, so your wheels might not be compatible with the final release. For this reason, we don't recommend distributing wheels until RC1, at which point 3.12 will be available in cibuildwheel without the flag. (#1507)

- ✨ Adds the ability to pass arguments to the container engine when the container is created, using the [CIBW_CONTAINER_ENGINE](https://cibuildwheel.readthedocs.io/en/stable/options/#container-engine) option. (#1499)

### v2.12.3

_19 April 2023_

- 🐛 Fix an import error when running on Python 3.7. (#1479)

### v2.12.2

_18 April 2023_

- 🐛 Fix a bug that caused an extra empty config-setting to be passed to the backend when CIBW_BUILD_FRONTEND is set to `build`. (#1474)
- 🐛 Fix a crash that occurred when overwriting an existing wheel on Windows. (#1464)
- 🛠 Pinned version updates, including CPython 3.10.11, 3.11.3, pip 23.1 and wheel 0.40.0.

### v2.12.1

_11 March 2023_

- 🐛 Fix a bug that prevented the use of CIBW_CONFIG_SETTINGS with the 'pip' build backend. (#1430)

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

If you are building Rust wheels, you can get by without some of the tricks required to make GLIBC work via manylinux; this is especially relevant for cross-compiling, which is easy with Rust. See [maturin-action](https://github.com/messense/maturin-action) for a tool that is optimized for building Rust wheels and cross-compiling.
