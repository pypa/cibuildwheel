---
title: Modern C++ standards
---

Building Python wheels with modern C++ standards (C++11 and later) requires a few tricks.


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
