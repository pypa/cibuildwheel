---
title: 'iOS'
---

# iOS builds

## Pre-requisites

You must be building on a macOS machine, with Xcode installed. The Xcode installation must have an iOS SDK available, with all license agreements agreed to by the user. To check if an iOS SDK is available, open the Xcode settings panel, and check the Platforms tab. This will also ensure that license agreements have been acknowledged.

Building iOS wheels also requires a working macOS Python installation. See the notes on [macOS builds](./macos.md) for details about configuration of the macOS environment.

## Specifying an iOS build

iOS is effectively 2 platforms - physical devices, and simulators. While the API for these two platforms are identical, the ABI is not compatible, even when dealing with a device and simulator with the same CPU architecture. For this reason, the architecture specification for iOS builds includes *both* the CPU architecture *and* the ABI that is being targeted. There are three possible values for architecture on iOS; the values match those used by `sys.implementation._multiarch` when running on iOS (with hyphens replaced with underscores, matching wheel filename normalization):

* `arm64_iphoneos` (for physical iOS devices);
* `arm64_iphonesimulator` (for iOS simulators running on Apple Silicon macOS machines); and
* `x64_64_iphonesimulator` (for iOS simulators running on Intel macOS machines).

By default, cibuildwheel will build wheels for all three of these targets.

If you need to specify different compilation flags or other properties on a per-ABI or per-CPU basis, you can use [configuration overrides](../../options/#overrides) with a `select` clause that targets the specific ABI or architecture. For example, consider the following example:

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

## iOS version compatibility

iOS builds will honor the `IPHONEOS_DEPLOYMENT_TARGET` environment variable to set the minimum supported API version for generated wheels. This will default to `13.0` if the environment variable isn't set.

## Cross platform builds

iOS builds are *cross platform builds*, as it not possible to run compilers and other build tools "on device". The pre-compiled iOS binaries used to support iOS builds include tooling that can convert any virtual environment into a cross platform virtual environment - that is, an environment that can run binaries on the build machine (macOS), but, if asked, will respond as if it is an iOS machine. This allows `pip`, `build`, and other build tools to perform iOS-appropriate behaviour.

## Build frontend support

iOS builds support both the `pip` and `build` build frontends. In principle, support for `uv` with the `build[uv]` frontend should be possible, but `uv` [doesn't currently have support for cross-platform builds](https://github.com/astral-sh/uv/issues/7957), and [doesn't have support for iOS (or Android) tags](https://github.com/astral-sh/uv/issues/8029).

## Build environment

The environment used to run builds does not inherit the full user environment - in particular, `PATH` is deliberately re-written. This is because UNIX C tooling doesn't do a great job differentiating between "macOS ARM64" and "iOS ARM64" binaries. If (for example) Homebrew is on the path when compilation commands are invoked, it's easy for a macOS version of a library to be linked into the iOS binary, rendering it unusable on iOS. To prevent this, iOS builds always force `PATH` to a "known minimal" path, that includes only the bare system utilities, and the iOS compiler toolchain.

If your project requires additional tools to build (such as `cmake`, `ninja`, or `rustc`), those tools must be explicitly declared as cross-build tools using [`CIBW_XBUILD_TOOLS`](../../options#xbuild-tools). *Any* tool used by the build process must be included in the `CIBW_XBUILD_TOOLS` list, not just tools that cibuildwheel will invoke directly. For example, if your build script invokes `cmake`, and the `cmake` script invokes `magick` to perform some image transformations, both `cmake` and `magick` must be included in your cross-build tools list.

## Tests

If tests have been configured, the test suite will be executed on the simulator matching the architecture of the build machine - that is, if you're building on an ARM64 macOS machine, the ARM64 wheel will be tested on an ARM64 simulator. It is not possible to use cibuildwheel to test wheels on other simulators, or on physical devices.

The iOS test environment can't support running shell scripts, so the [`CIBW_TEST_COMMAND`](../../options#test-command) value must be specified as if it were a command line being passed to `python -m ...`. In addition, the project must use [`CIBW_TEST_SOURCES`](../../options#test-sources) to specify the minimum subset of files that should be copied to the test environment. This is because the test must be run "on device", and the simulator device will not have access to the local project directory.

The test process uses the same testbed used by CPython itself to run the CPython test suite. It is an Xcode project that has been configured to have a single Xcode "XCUnit" test - the result of which reports the success or failure of running `python -m <CIBW_TEST_COMMAND>`.
