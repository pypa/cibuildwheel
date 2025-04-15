# Android builds

## Prerequisites

cibuildwheel can build and test Android wheels on any POSIX platform supported by the
Android development tools, which currently means Linux x86_64, macOS ARM64 or macOS
x86_64.

Building Android wheels requires the build machine to have a working Python executable
of the same version. See the notes on [Linux](linux.md) and [macOS](macos.md) for
details of how this is installed.

If you already have an Android SDK, export the `ANDROID_HOME` environment variable to
point at its location. Otherwise, here's how to install it:

* Download the "Command line tools" from <https://developer.android.com/studio>.
* Create a directory `android-sdk/cmdline-tools`, and unzip the command line
  tools package into it.
* Rename `android-sdk/cmdline-tools/cmdline-tools` to
  `android-sdk/cmdline-tools/latest`.
* `export ANDROID_HOME=/path/to/android-sdk`

cibuildwheel will automatically use the SDK's `sdkmanager` to install any packages it
needs.

It also requires the following commands to be on the `PATH`:

* `curl`
* `java` (or set the `JAVA_HOME` environment variable)

## Android version compatibility

Android builds will honor the `api_level` environment variable to set the minimum
supported [API level](https://developer.android.com/tools/releases/platforms) for
generated wheels. This will default to the minimum API level of the selected Python
version.

## Build frontend support

Android builds only support the `build` frontend. In principle, support for the
`build[uv]` frontend should be possible, but `uv` [doesn't currently have support for
cross-platform builds](https://github.com/astral-sh/uv/issues/7957), and [doesn't have
support for iOS or Android wheel tags](https://github.com/astral-sh/uv/issues/8029).

## Cross platform builds

Android builds are *cross platform builds*, as cibuildwheel does not support running
compilers and other build tools "on device". The supported build platforms (listed
above) can be used to build wheels for any supported Android architecture. However,
wheels can only be *tested* on a machine of the same architecture – see the section
below.

## Tests

If tests have been configured, the test suite will be executed on a Gradle-managed
emulator matching the architecture of the build machine - for example, if you're
building on an ARM64 machine, an ARM64 wheel can be tested on an ARM64 emulator.
Cross-architecture testing is not supported.

On Linux, the emulator needs access to the KVM virtualization interface, and a DISPLAY
environment variable pointing at an X server. Xvfb is acceptable.

The Android test environment can't support running shell scripts, so the
[`CIBW_TEST_COMMAND`](../options.md#test-command) value must be specified as if it were
a command line being passed to `python -m ...`. In addition, the project must use
[`CIBW_TEST_SOURCES`](../options.md#test-sources) to specify the minimum subset of files
that should be copied to the test environment. This is because the test must be run "on
device", and the device will not have access to the local project directory.

The test process uses the same testbed used by CPython itself to run the CPython test
suite. It is a Gradle project that has been configured to have a single JUnit - the
result of which reports the success or failure of running `python -m
<CIBW_TEST_COMMAND>`.
