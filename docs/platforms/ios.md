---
title: 'iOS'
---

# iOS builds

## Pre-requisites

You must be building on a macOS machine, with Xcode installed. The Xcode installation must have an iOS SDK available, with all license agreements agreed to by the user. To check if an iOS SDK is available, open the Xcode settings panel, and check the Platforms tab. This will also ensure that license agreements have been acknowledged.

Building iOS wheel also requires a working macOS Python configuration. See the notes on [macOS builds](./macos.md) for details about configuration of the macOS environment.

## Specifying an iOS build

iOS is effectively 2 platforms - physical devices, and simulators. While the API for these two platforms are identical, the ABI is not compatible, even when dealing with a device and simulator with the same CPU architecture. For this reason, iOS support includes 3 values for `CIBW_PLATFORM`:

* `iphoneos` (for devices);
* `iphonesimulator` (for simulators); and
* `ios` for the combination of the two.

A full build, using the `ios` platform, will results in 3 wheels (1 device, 2 simulator):

* An ARM64 wheel for iOS devices;
* An ARM64 wheel for the iOS simulator; and
* An x86_64 wheel for the iOS simulator.

Alternatively, you can build only wheels for iOS devices by using the `iphoneos` platform; or only wheels for iOS simulators by using the `iphonesimulator`.

## iOS version compatibility

iOS builds will honor the `IPHONEOS_DEPLOYMENT_TARGET` environment variable to set the minimum supported API version for generated wheels. This will default to `13.0` if the environment variable isn't set.

## Cross platform builds

iOS builds are *cross platform builds*, as it not possible to run compilers and other build tools "on device". The pre-compiled iOS binaries used to support iOS builds include tooling that can convert any virtual environment into a cross platform virtual environment - that is, an environment that can run binaries on the build machine (macOS), but, if asked, will respond as if it is an iOS machine. This allows pip, build, and other build tools to perform iOS-appropriate behaviour.

## Build frontend support

iOS builds support both the pip and build build frontends. In principle, support for uv with the `build[uv]` frontend should be possible, but uv [doesn't currently have support for cross-platform builds](https://github.com/astral-sh/uv/issues/7957), and [doesn't have support for iOS (or Android) tags](https://github.com/astral-sh/uv/issues/8029).

## Build environment

The environment used to run builds does not inherit the full user environment - in particular, `PATH` is deliberately re-written. This is because UNIX C tooling doesn't do a great job differentiating between "macOS ARM64" and "iOS ARM64" binaries. If (for example) Homebrew is on the path when compilation commands are invoked, it's easy for a macOS version of a library to be linked into the iOS binary, rendering it unusable on iOS. To prevent this, iOS builds always force `PATH` to a "known minimal" path, that includes only the bare system utilities, plus the current user's cargo folder (to facilitate Rust builds).

## Tests

If tests have been configured, the test suite will be executed on the simulator matching the architecture of the build machine - that is, if you're building on an ARM64 macOS machine, the ARM64 wheel will be tested on an ARM64 simulator. It is not possible to use cibuildwheel to test wheels on other simulators, or on physical devices.

The iOS test environment can't support running shell scripts, so the `CIBW_TEST_COMMAND` value must be specified as if it were a command line being passed to `python -m ...`. In addition, the test itself must be run "on device", so the local project directory cannot be used to run tests. Instead, the entire project sources must be copied onto the test device; or the project must use `CIBW_TEST_SOURCES` to specify the minimum subset of files that should be copied to the test environment.

The test process uses the same testbed used by CPython itself to run the CPython test suite. It is an Xcode project that has been configured to have a single Xcode "XCUnit" test - the result of which reports the success or failure of running `python -m <CIBW_TEST_COMMAND>`.

!!! warning
    iOS tests cannot be run in parallel.

    The CPython iOS test runner requires starting a simulator to run the tests. There is [a known issue with the CPpython iOS test runner](https://github.com/python/cpython/issues/129200) that can cause problems starting multiple simulators in parallel. If you attempt to start multiple testbed instances at the same time, you may see a failure that looks like:

    ```console
    note: Run script build phase 'Prepare Python Binary Modules' will be run during every build because the option to run the script phase "Based on dependency analysis" is unchecked. (in target 'iOSTestbed' from project 'iOSTestbed')
    note: Run script build phase 'Install Target Specific Python Standard Library' will be run during every build because the option to run the script phase "Based on dependency analysis" is unchecked. (in target 'iOSTestbed' from project 'iOSTestbed')
    Found more than one new device: {'5CAA0336-9CE1-4222-BFE3-ADA405F766DE', 'DD108383-685A-4400-BF30-013AA82C4A61'}
    make: *** [testios] Error 1
    program finished with exit code 2
    ```

    However, even when this issue is resolved, you likely don't want to start too many iOS simulators on the same machine. It is advisable to either run iOS tests sequentially, or use use a feature such as [pytest's `loadgroup` mechanism](https://pytest-xdist.readthedocs.io/en/stable/distribution.html) to ensure that all iOS tests run sequentially.

    Note that this only applies to running multiple iOS test *projects* in parallel. A single test suite can run in parallel on a single iOS simulator; this limitation only applies to starting multiple independent simulators. A normal cibuildwheel run will only start one iOS simulator at a time; if you perform multiple cibuildwheel runs in parallel on the same machine, you might see this problem.
