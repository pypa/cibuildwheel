---
title: Modern C++ standards
---

# Modern C++ standards

Building Python wheels with modern C++ standards (C++11 and later) requires a few tricks.


## manylinux2014 and C++20

The past end-of-life `manylinux2014` image (based on CentOS 7) contains a version of GCC and libstdc++ that only supports C++17 and earlier standards.

`manylinux_2_28` are newer and support all C++ standards (up to C++20).

## macOS and deployment target versions

The [`MACOSX_DEPLOYMENT_TARGET` environment variable](platforms.md#macos-version-compatibility) is used to set the minimum deployment target for macOS.

However, to enable modern C++ standards, the deployment target needs to be set high enough (since older OS X/macOS versions did not have the necessary modern C++ standard library).

To get C++17 support, Xcode 9.3+ is needed, requiring at least macOS 10.13 on the build machine. To use C++17 library features and link against the C++ runtime library, set `MACOSX_DEPLOYMENT_TARGET` to `"10.13"` or `"10.14"` (or higher) - macOS 10.13 offers partial C++17 support (e.g., the filesystem header is in experimental, offering `#include <experimental/filesystem>` instead of `#include <filesystem>`); macOS 10.14 has full C++17 support. CPython 3.12+ require 10.13+ anyway.

However, if only C++17 compiler and standard template library (STL) features are used (not needing a C++17 runtime) it might be possible to set `MACOSX_DEPLOYMENT_TARGET` to a lower value, such as `"10.9"`. To find out if this is the case, try compiling and running with a lower `MACOSX_DEPLOYMENT_TARGET`: if C++17 features are used that require a more recent deployment target, building the wheel should fail.

For more details see https://en.cppreference.com/w/cpp/compiler_support, https://en.wikipedia.org/wiki/Xcode, and https://xcodereleases.com/: Xcode 10 needs macOS 10.13 and Xcode 11 needs macOS 10.14.
