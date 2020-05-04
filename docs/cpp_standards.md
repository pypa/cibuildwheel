---
title: Modern C++ standards
---

Building Python wheels with modern C++ standards (C++11 and later) requires a few tricks.


## Python 2.7 and C++17

The Python 2.7 header files use the `register` keyword, which is [reserved and unused from C+17 onwards](https://en.cppreference.com/w/cpp/keyword/register). Compiling a wheel for Python 2.7 with the C++17 standard is still possible to allow usage of `register` using proper flag `-Wno-register` for gcc/clang and `/wd5033` for MSVC.

## manylinux1 and C++14
The default `manylinux1` image (based on CentOS 5) contains a version of GCC and libstdc++ that only supports C++11 and earlier standards. There are however ways to compile wheels with the C++14 standard (and later): https://github.com/pypa/manylinux/issues/118

`manylinux2010` and `manylinux2014` are newer and support all C++ standards (up to C++17).

## macOS and deployment target versions

OS X/macOS allows you to specify a so-called "deployment target" version that will ensure backwards compatibility with older versions of macOS. One way to do this is by setting the `MACOSX_DEPLOYMENT_TARGET` environment variable.

However, to enable modern C++ standards, the deploment target needs to be set high enough (since older OS X/macOS versions did not have the necessary modern C++ standard library).

To get C++11 and C++14 support, `MACOSX_DEPLOYMENT_TARGET` needs to be set to (at least) `"10.9"`. By default, `cibuildwheel` already does this, building 64-bit-only wheels for macOS 10.9 and later.

To get C++17 support, Xcode 9.3+ is needed, requiring at least macOS 10.13 on the build machine. To use C++17 library features and link against the C++ runtime library, set `MACOSX_DEPLOYMENT_TARGET` to `"10.13"` or `"10.14"` (or higher) - macOS 10.13 offers partial C++17 support (e.g., the filesystem header is in experimental, offering `#include <experimental/filesystem>` instead of `#include <filesystem>`); macOS 10.14 has full C++17 support.

However, if only C++17 compiler and standard template library (STL) features are used (not needing a C++17 runtime) it might be possible to set `MACOSX_DEPLOYMENT_TARGET` to a lower value, such as `"10.9"`. To find out if this is the case, try compiling and running with a lower `MACOSX_DEPLOYMENT_TARGET`: if C++17 features are used that require a more recent deployment target, building the wheel should fail.

For more details see https://en.cppreference.com/w/cpp/compiler_support, https://en.wikipedia.org/wiki/Xcode, and https://xcodereleases.com/: Xcode 10 needs macOS 10.13 and Xcode 11 needs macOS 10.14.

## Windows and Python 2.7

Visual C++ for Python 2.7 does not support modern C++ standards (i.e., C++11 and later). When building on Appveyor, you will need to either use the "Visual Studio 2017" or "Visual Studio 2019" image, but Python 2.7 is not supported on these images - skip it by setting `CIBW_SKIP=cp27-win*`.

There is an optional workaround for this, though: the pybind11 project argues and shows that it is [possible to compile Python 2.7 extension with a newer compiler](https://pybind11.readthedocs.io/en/stable/faq.html#working-with-ancient-visual-studio-2008-builds-on-windows) and has an example project showing how to do this: https://github.com/pybind/python_example. The main catch is that a user might need to install [a newer "Microsoft Visual C++ Redistributable"](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads), since the newer C++ standard library's binaries are not included by default with the Python 2.7 installation.

Forcing `distutils` or `setuptools` to use a more recent version of MSVC that supports modern C++ can be done in the following way:

1. Set the environment variables `DISTUTILS_USE_SDK=1` and `MSSdk=1`. These two environment variables will tell `distutils`/`setuptools` to not search and set up a build environment that uses Visual C++ for Python 2.7 (aka. MSVC 9).
2. Set up the build Visual Studio build environment you want to use, making sure that e.g. `PATH` contains `cl`, `link`, etc.
    - Usually, this can be done through `vcvarsall.bat x86` or `vcvarsall.bat x64`. The exact location of this file depends on the installation, but the default path for VS 2019 Community (e.g. used in AppVeyor's `Visual Studio 2019` image) is `C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat`. **Note**: `vcvarsall.bat` changes the environment variables, so this cannot be run in a subprocess/subshell and consequently running `vsvarsall.bat` in `CIBW_BEFORE_BUILD` does not have any effect.
    - In Azure Pipelines, [a `VSBuild` task is available](https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/build/visual-studio-build) and GitHub Actions has [an action `microsoft/setup-msbuild`](https://github.com/microsoft/setup-msbuild) that help setting up the Visual Studio environment.
3. Next, call `cibuildwheel`. Unfortunately, MSVC has separate toolchains for compiling 32-bit and 64-bit, so you will need to run `cibuildwheel` twice: once with `CIBW_BUILD=*-win32` after setting up the `x86` build environment, and once with `CIBW_BUILD=*-win_amd64` in a `x64` enviroment (see previous step).
