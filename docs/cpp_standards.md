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

OS X/macOS allows you to specify a so-called "deployment target" version that will ensure backwards compatibility with older versions of macOS. One way to do this is by setting the `MACOSX_DEPLOYMENT_TARGET` environment variable. If not set, Python will set this variable to the version the Python distribution itself was compiled on (10.6 or 10.9, for the python.org packages), when creating the wheel.

However, to enable modern C++ standards, the deploment target needs to be set high enough (since older OS X/macOS versions did not have the necessary modern C++ standard library).

To get C++11 and C++14 support, `MACOSX_DEPLOYMENT_TARGET` needs to be set to (at least) `"10.9"`. By default, `cibuildwheel` already does this, building 64-bit-only wheels for macOS 10.9 and later.

To get C++17 support, set `MACOSX_DEPLOYMENT_TARGET` to (at least) `"10.13"` or `"10.14"` (macOS 10.13 offers partial C++17 support; e.g., the filesystem header is in experimental, offering `#include <experimental/filesystem>` instead of `#include <filesystem>`; macOS 10.14 has full C++17 support).

For more details see https://en.cppreference.com/w/cpp/compiler_support and https://xcodereleases.com/: Xcode 10 needs macOS 10.13 and Xcode 11 needs macOS 10.14.

## Windows and Python 2.7

Visual C++ for Python 2.7 does not support modern standards of C++. When building on Appveyor, you will need to either use the "Visual Studio 2017" or "Visual Studio 2019" image, but Python 2.7 is not supported on these images - skip it by setting `CIBW_SKIP=cp27-win*`.

There is an optional workaround for this, though: the pybind11 project argues and shows that it is [possible to compile Python 2.7 extension with a newer compiler](https://pybind11.readthedocs.io/en/stable/faq.html#working-with-ancient-visual-studio-2008-builds-on-windows) and has an example project showing how to do this: https://github.com/pybind/python_example. The main catch is that a user might need to install a newer "Microsoft Visual C++ Redistributable", since the newer C++ standard libraries are not included by default with the Python 2.7 installation.
