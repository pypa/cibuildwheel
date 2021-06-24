---
title: Modern C++ standards
---

Building Python wheels with modern C++ standards (C++11 and later) requires a few tricks.


## manylinux and C++
The `manylinux*` standards imply a limit on which C++ standard you can use. There are workarounds to this, and `cibuildwheel` uses some workarounds by default. You should be aware of them!

Consider that the `manylinux*` standards constrain _symbol versions_ in `libstdc++.so`. So when *dynamically linking* to `libstdc++.so`, the desired `manylinux*` standard constrains the gcc version, and thus constrains the C++ standard.

Cross-referencing [current manylinux standards](https://github.com/mayeut/pep600_compliance/blob/f86a7d7c153cc45aa3f2add6ffcf610c80501657/pep600_compliance/tools/policy.json) with [gcc's symbol versions](https://gcc.gnu.org/onlinedocs/libstdc++/manual/abi.html) and [libstdc++'s language support](https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html), we have:
 * `manylinux1`: gcc 4.1.x
 * `manylinux2010`: gcc 4.4.x
 * `manylinux2014`: gcc 4.8.x
 * `manylinux_2_24`: gcc 6.x (stable C++14 ABI)
 * `manylinux_2_27`: gcc 7.x (stable C++14 ABI)

([The first release of a complete and stable C++17 ABI is gcc 9.1](https://gcc.gnu.org/onlinedocs/libstdc++/manual/status.html#status.iso.2017), but as of writing there is no official `manylinux*` standard that supports this version. Prior standards like C++11 *are* supported, but gcc doesn't document the per-version support as clearly as C++14 and later)

We *can* use newer C++ standards and support older `manylinux*`, if we use *static linking*.

The default `manylinux1`, `manylinux2010` and `manylinux2014` docker images include *more recent* gcc than the one matched to their standard. These CentOS-based images use automagic *selective static linking* for newer `libstdc++.so` symbols, and dynamic linking for older ones (this is done by having `libstdc++.so` from the `devtools` package be a linker script, and splitting newer symbols into a static library).

The debian-based `manylinux_2_24` image *does not* do selective static linking as of writing. See https://github.com/pypa/manylinux/issues/1012

As of 2021-06-24, the gcc versions on each (x86-64) image are:
 * `manylinux1`: gcc 4.8.2 (C++11 stable)
 * `manylinux2010`: gcc 8.3.1 (C++14 stable)
 * `manylinux2014`: gcc 9.3.1 (C++17 stable)
 * `manylinux_2_24`: gcc 6.3.0 (C++14 stable)

Each gcc version may support later C++ standards incompletely or experimentally. In some cases gcc may support a standard with an unstable ABI, but this won't matter with static linking (so using C++17 on `manylinux2010` will probably just work). You will have to experiment for yourself to see what works.

If you hit an edge case with selective static linking, or want to try to support an older `manylinux*` standard, you can use unconditional static linking with `LDFLAGS=-static-libstdc++`. Note that this will bloat your wheels, and pypi *does* have a limit on total project size!

If you really want dynamic linking with a newer C++ standard, you could just declare the non-specific `linux` platform tag, instead of a `manylinux*` tag. Use `AUDITWHEEL_PLAT=linux`.

For more information, see https://github.com/pypa/manylinux/issues/118

## macOS and deployment target versions

OS X/macOS allows you to specify a so-called "deployment target" version that will ensure backwards compatibility with older versions of macOS. One way to do this is by setting the `MACOSX_DEPLOYMENT_TARGET` environment variable.

However, to enable modern C++ standards, the deploment target needs to be set high enough (since older OS X/macOS versions did not have the necessary modern C++ standard library).

To get C++11 and C++14 support, `MACOSX_DEPLOYMENT_TARGET` needs to be set to (at least) `"10.9"`. By default, `cibuildwheel` already does this, building 64-bit-only wheels for macOS 10.9 and later.

To get C++17 support, Xcode 9.3+ is needed, requiring at least macOS 10.13 on the build machine. To use C++17 library features and link against the C++ runtime library, set `MACOSX_DEPLOYMENT_TARGET` to `"10.13"` or `"10.14"` (or higher) - macOS 10.13 offers partial C++17 support (e.g., the filesystem header is in experimental, offering `#include <experimental/filesystem>` instead of `#include <filesystem>`); macOS 10.14 has full C++17 support.

However, if only C++17 compiler and standard template library (STL) features are used (not needing a C++17 runtime) it might be possible to set `MACOSX_DEPLOYMENT_TARGET` to a lower value, such as `"10.9"`. To find out if this is the case, try compiling and running with a lower `MACOSX_DEPLOYMENT_TARGET`: if C++17 features are used that require a more recent deployment target, building the wheel should fail.

For more details see https://en.cppreference.com/w/cpp/compiler_support, https://en.wikipedia.org/wiki/Xcode, and https://xcodereleases.com/: Xcode 10 needs macOS 10.13 and Xcode 11 needs macOS 10.14.
