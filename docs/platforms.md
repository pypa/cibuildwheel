---
title: Platforms
---
# Platforms

## Linux

If you've got [Docker](https://www.docker.com/products/docker-desktop) installed on your development machine, you can run a Linux build.

!!! tip
    You can run the Linux build on any platform. Even Windows can run
    Linux containers these days, but there are a few hoops to jump
    through. Check [this document](https://docs.microsoft.com/en-us/virtualization/windowscontainers/quick-start/quick-start-windows-10-linux)
    for more info.

Because the builds are happening in manylinux Docker containers, they're perfectly reproducible.

The only side effect to your system will be docker images being pulled.

## macOS

### Pre-requisites

Pre-requisite: you need to have native build tools installed.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Xcode version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: /Users/Matt/Library/Caches/cibuildwheel`).

You can override the cache folder using the `CIBW_CACHE_PATH` environment variable.

!!! warning
    cibuildwheel uses official python.org macOS installers for CPython but those can only be installed globally.

    In order not to mess with your system, cibuildwheel won't install those if they are missing. Instead, it will error out with a message to let you install the missing CPython:

    ```console
    Error: CPython 3.9 is not installed.
    cibuildwheel will not perform system-wide installs when running outside of CI.
    To build locally, install CPython 3.9 on this machine, or, disable this version of Python using CIBW_SKIP=cp39-macosx_*

    Download link: https://www.python.org/ftp/python/3.9.8/python-3.9.8-macosx10.9.pkg
    ```

### macOS Version Compatibility

macOS builds will honor the `MACOSX_DEPLOYMENT_TARGET` environment variable to control the minimum supported macOS version for generated wheels. The lowest value you can set `MACOSX_DEPLOYMENT_TARGET` is as follows:

| Arch  | Python version range | Minimum target |
|-------|----------------------|----------------|
| Intel | CPython 3.8-3.11     | 10.9           |
| Intel | CPython 3.12+        | 10.13          |
| AS    | CPython or PyPy      | 11             |
| Intel | PyPy 3.8             | 10.13          |
| Intel | PyPy 3.9+            | 10.15          |

If you set the value lower, cibuildwheel will cap it to the lowest supported value for each target as needed.

!!! note
    For Rust-based extensions, `Rustc` requires `MACOSX_DEPLOYMENT_TARGET` to be at
    least 10.12. However, `cibuildwheel` defaults to 10.9 for
    **Intel / CPython 3.8-3.11** builds. Users must manually set
    `MACOSX_DEPLOYMENT_TARGET` to 10.12 or higher when building Rust extensions.

### Universal builds

By default, macOS builds will build a single architecture wheel, using the build machine's architecture. If you need to support both x86_64 and Apple Silicon, you can use the `CIBW_ARCHS` environment variable to specify the architectures you want to build, or the value `universal2` to build a multi-architecture wheel. cibuildwheel will test x86_64 wheels (or the x86_64 slice of a `universal2` wheel) when running on Apple Silicon hardware, but it is *not* possible to test Apple Silicon wheels on x86_64 hardware.

## Windows

### Pre-requisites

You must have native build tools (i.e., Visual Studio) installed.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Visual Studio version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: C:\Users\Matt\AppData\Local\pypa\cibuildwheel\Cache`).

You can override the cache folder using the ``CIBW_CACHE_PATH`` environment variable.

## Pyodide (WebAssembly) builds (experimental) {: #pyodide}

### Prerequisites

You need to have a matching host version of Python (unlike all other cibuildwheel platforms). Linux host highly recommended; macOS hosts may work (e.g. invoking `pytest` directly in [`CIBW_TEST_COMMAND`](options.md#test-command) is [currently failing](https://github.com/pyodide/pyodide/issues/4802)) and Windows hosts will not work.

### Specifying a pyodide build

You must target pyodide with `--platform pyodide` (or use `--only` on the identifier).

## iOS

### Pre-requisites

You must be building on a macOS machine, with Xcode installed. The Xcode installation must have an iOS SDK available, with all license agreements agreed to by the user. To check if an iOS SDK is available, open the Xcode settings panel, and check the Platforms tab. This will also ensure that license agreements have been acknowledged.

Building iOS wheels also requires a working macOS Python installation. See the notes on [macOS builds](#macos) for details about configuration of the macOS environment.

### Specifying an iOS build

iOS is effectively 2 platforms - physical devices, and simulators. While the API for these two platforms are identical, the ABI is not compatible, even when dealing with a device and simulator with the same CPU architecture. For this reason, the architecture specification for iOS builds includes *both* the CPU architecture *and* the ABI that is being targeted. There are three possible values for architecture on iOS; the values match those used by `sys.implementation._multiarch` when running on iOS (with hyphens replaced with underscores, matching wheel filename normalization):

* `arm64_iphoneos` (for physical iOS devices);
* `arm64_iphonesimulator` (for iOS simulators running on Apple Silicon macOS machines); and
* `x64_64_iphonesimulator` (for iOS simulators running on Intel macOS machines).

By default, cibuildwheel will build wheels for all three of these targets.

If you need to specify different compilation flags or other properties on a per-ABI or per-CPU basis, you can use [configuration overrides](configuration.md#overrides) with a `select` clause that targets the specific ABI or architecture. For example, consider the following example:

```
[tool.cibuildwheel.ios]
test-sources = ["tests"]
test-requires = ["pytest"]

[[tool.cibuildwheel.overrides]]
select = "*_iphoneos"
environment.PATH = "/path/to/special/device/details:..."

[[tool.cibuildwheel.overrides]]
select = "*-ios_arm64_*"
inherit.test-requires = "append"
test-requires = ["arm64-testing-helper"]
```

This configuration would:

 * Specify a `test-sources` and `test-requires` for all iOS targets;
 * Add a `PATH` setting that will be used on physical iOS devices; and
 * Add `arm64-testing-helper` to the test environment for all ARM64 iOS devices (whether simulator or device).

### iOS version compatibility

iOS builds will honor the `IPHONEOS_DEPLOYMENT_TARGET` environment variable to set the minimum supported API version for generated wheels. This will default to `13.0` if the environment variable isn't set.

### Cross platform builds

iOS builds are *cross platform builds*, as it not possible to run compilers and other build tools "on device". The pre-compiled iOS binaries used to support iOS builds include tooling that can convert any virtual environment into a cross platform virtual environment - that is, an environment that can run binaries on the build machine (macOS), but, if asked, will respond as if it is an iOS machine. This allows `pip`, `build`, and other build tools to perform iOS-appropriate behaviour.

### Build frontend support

iOS builds support both the `pip` and `build` build frontends. In principle, support for `uv` with the `build[uv]` frontend should be possible, but `uv` [doesn't currently have support for cross-platform builds](https://github.com/astral-sh/uv/issues/7957), and [doesn't have support for iOS (or Android) tags](https://github.com/astral-sh/uv/issues/8029).

### Build environment

The environment used to run builds does not inherit the full user environment - in particular, `PATH` is deliberately re-written. This is because UNIX C tooling doesn't do a great job differentiating between "macOS ARM64" and "iOS ARM64" binaries. If (for example) Homebrew is on the path when compilation commands are invoked, it's easy for a macOS version of a library to be linked into the iOS binary, rendering it unusable on iOS. To prevent this, iOS builds always force `PATH` to a "known minimal" path, that includes only the bare system utilities, plus the current user's cargo folder (to facilitate Rust builds).

### Tests

If tests have been configured, the test suite will be executed on the simulator matching the architecture of the build machine - that is, if you're building on an ARM64 macOS machine, the ARM64 wheel will be tested on an ARM64 simulator. It is not possible to use cibuildwheel to test wheels on other simulators, or on physical devices.

The iOS test environment can't support running shell scripts, so the [`CIBW_TEST_COMMAND`](options.md#test-command) value must be specified as if it were a command line being passed to `python -m ...`. In addition, the project must use [`CIBW_TEST_SOURCES`](options.md#test-sources) to specify the minimum subset of files that should be copied to the test environment. This is because the test must be run "on device", and the simulator device will not have access to the local project directory.

The test process uses the same testbed used by CPython itself to run the CPython test suite. It is an Xcode project that has been configured to have a single Xcode "XCUnit" test - the result of which reports the success or failure of running `python -m <CIBW_TEST_COMMAND>`.
