---
title: 'macOS'
---

# macOS builds

## Pre-requisites

Pre-requisite: you need to have native build tools installed.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Xcode version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: /Users/Matt/Library/Caches/cibuildwheel`).

You can override the cache folder using the `CIBW_CACHE_PATH` environment variable.

!!! warning
    cibuildwheel uses official python.org macOS installers for CPython but those can only be installed globally.

    In order not to mess with your system, cibuildwheel won't install those if they are missing. Instead, it will error out with a message to let you install th missing CPython:

    ```console
    Error: CPython 3.9 is not installed.
    cibuildwheel will not perform system-wide installs when running outside of CI.
    To build locally, install CPython 3.9 on this machine, or, disable this version of Python using CIBW_SKIP=cp39-macosx_*

    Download link: https://www.python.org/ftp/python/3.9.8/python-3.9.8-macosx10.9.pkg
    ```

## Universal builds

By default, macOS builds will build a single architecture wheel, using the build machine's architecture. If you need to support both x86_64 and Apple Silicon, you can use the `CIBW_ARCHS` environment variable to specify the architectures you want to build, or the value `universal2` to build a multi-architecture wheel. cibuildwheel will test x86_64 wheels (or the x86_64 slice of a `universal2` wheel) when running on Apple Silicon hardware, but it is *not* possible to test Apple Silicon wheels on x86_64 hardware.
