---
title: Platforms
---
# Platforms

## Linux {: #linux}

### System requirements

If you've got [Docker](https://www.docker.com/get-started/) installed on your development machine, you can run a Linux build.

!!! tip
    You can run the Linux build on any platform. Even Windows can run
    Linux containers these days, but there are a few hoops to jump
    through. Check [this document](https://docs.microsoft.com/en-us/virtualization/windowscontainers/quick-start/quick-start-windows-10-linux)
    for more info.

Because the builds are happening in manylinux Docker containers, they're perfectly reproducible.

The only side effect to your system will be docker images being pulled.

### Build containers {: #linux-containers}

Linux wheels are built in [`manylinux`/`musllinux` containers](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 600](https://www.python.org/dev/peps/pep-0600/) / [PEP 656](https://www.python.org/dev/peps/pep-0656/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:

-   Programs and libraries are not installed on the CI runner host, but rather should be installed inside the container - using `yum` for `manylinux2014`, `apt-get` for `manylinux_2_31`, `dnf` for `manylinux_2_28` and `apk` for `musllinux_1_1` or `musllinux_1_2`, or manually. The same goes for environment variables that are potentially needed to customize the wheel building.

    `cibuildwheel` supports this by providing the [`environment`](options.md#environment) and [`before-all`](options.md#before-all) options to setup the build environment inside the running container.

-   The project directory is copied into the container as `/project`, the output directory for the wheels to be copied out is `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that `/host` is not available on CircleCI and GitLab CI due to their Docker policies.

-   Alternative Docker images can be specified with the `manylinux-*-image`/`musllinux-*-image` options to allow for a custom, preconfigured build environment for the Linux builds. See [options](options.md#linux-image) for more details.

## macOS {: #macos}

### System requirements

You need to have native build tools installed. Use `xcode-select --install` to install the Xcode command line tools.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Xcode version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: /Users/Matt/Library/Caches/cibuildwheel`). You can override the cache folder using the `CIBW_CACHE_PATH` environment variable.

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

macOS allows you to specify a "deployment target" version that will ensure backwards compatibility with older versions of macOS. For most projects, the way to do this is to set the `MACOSX_DEPLOYMENT_TARGET` environment variable.

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

### macOS architectures

`cibuildwheel` supports both native builds and cross-compiling between `arm64` (Apple Silicon) and `x86_64` (Intel) architectures, including the cross-compatible `universal2` format. By default, macOS builds will build a single architecture wheel, using the build machine's architecture.

If you need to support both `x86_64` and Apple Silicon, you can use the [`macos.archs`](options.md#archs) setting to specify the architectures you want to build, or the value `universal2` to build a multi-architecture wheel. cibuildwheel _will_ test `x86_64` wheels (or the `x86_64` slice of a `universal2` wheel) when running on Apple Silicon hardware using Rosetta 2 emulation, but it is *not* possible to test Apple Silicon wheels on `x86_64` hardware.

#### Overview of Mac architectures

##### `x86_64`

The traditional wheel for Apple, loads on Intel machines, and on
Apple Silicon when running Python under Rosetta 2 emulation.

Due to a change in naming, Pip 20.3+ (or an installer using packaging 20.5+)
is required to install a binary wheel on macOS Big Sur.

##### `arm64`

The native wheel for macOS on Apple Silicon.

##### `universal2`

This wheel contains both architectures, causing it to be up to twice the
size (data files do not get doubled, only compiled code).

The dual-architecture `universal2` has a few benefits, but a key benefit
to a universal wheel is that a user can bundle these wheels into an
application and ship a single binary.

However, if you have a large library, then you might prefer to ship
the two single-arch wheels instead - `x86_64` and `arm64`. In rare cases,
you might want to build all three, but in that case, pip will not download
the universal wheels, because it prefers the most specific wheel
available.

#### What to provide?

Opinions vary on which of arch-specific or `universal2` wheels are best - some packagers prefer `universal2` because it's one wheel for all Mac users, so simpler, and easier to build into apps for downstream users. However, because they contain code for both architectures, their file size is larger, meaning they consume more disk space and bandwidth, and are harder to build for some projects.

See [GitHub issue 1333](https://github.com/pypa/cibuildwheel/issues/1333) for more discussion.

#### How?

It's easiest to build `x86_64` wheels on `x86_64` runners, and `arm64` wheels on `arm64` runners.

On GitHub Actions, `macos-14` runners are `arm64`, and `macos-13` runners are `x86_64`. So all you need to do is ensure both are in your build matrix.

#### Cross-compiling

If your CI provider doesn't offer arm64 runners yet, or you want to create `universal2`, you'll have to cross-compile. Cross-compilation can be enabled by adding extra archs to the [`CIBW_ARCHS_MACOS` option](options.md#archs) - e.g. `CIBW_ARCHS_MACOS="x86_64 universal2"`. Cross-compilation is provided by Xcode toolchain v12.2+.

Regarding testing,

- On an arm64 runner, it is possible to test `x86_64` wheels and both parts of a `universal2` wheel using Rosetta 2 emulation.
- On an `x86_64` runner, arm64 code can be compiled but it can't be tested. `cibuildwheel` will raise a warning to notify you of this - these warnings can be silenced by skipping testing on these platforms: `test-skip = ["*_arm64", "*_universal2:arm64"]`.

!!! note
    If your project uses **Poetry** as a build backend, cross-compiling on macOS [does not currently work](https://github.com/python-poetry/poetry/issues/7107). In some cases arm64 wheels can be built but their tags will be incorrect, with the platform tag showing `x86_64` instead of `arm64`.

    As a workaround, the tag can be fixed before running delocate to repair the wheel. The [`wheel tags`](https://wheel.readthedocs.io/en/stable/reference/wheel_tags.html) command is ideal for this. See [this workflow](https://gist.github.com/anderssonjohan/49f07e33fc5cb2420515a8ac76dc0c95#file-build-pendulum-wheels-yml-L39-L53) for an example usage of `wheel tags`.


## Windows {: #windows}

### System requirements

You must have native build tools (i.e., Visual Studio) installed.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Visual Studio version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: C:\Users\Matt\AppData\Local\pypa\cibuildwheel\Cache`). You can override the cache folder using the ``CIBW_CACHE_PATH`` environment variable.

### Windows ARM64 builds {: #windows-arm64}

`cibuildwheel` supports cross-compiling `ARM64` wheels on all Windows runners, but a native `ARM64` runner is required for testing. On non-native runners, tests for `ARM64` wheels will be automatically skipped with a warning. Add `"*-win_arm64"` to your `test-skip` setting to suppress the warning.

Cross-compilation on Windows relies on a supported build backend. Supported backends use an environment variable to specify their target platform (the one they are compiling native modules for, as opposed to the one they are running on), which is set in [cibuildwheel's windows.py](https://github.com/pypa/cibuildwheel/blob/main/cibuildwheel/platforms/windows.py) before building. Currently, `setuptools>=65.4.1` and `setuptools_rust` are the only supported backends.

By default, `ARM64` is not enabled when running on non-`ARM64` runners. Use [`CIBW_ARCHS`](options.md#archs) to select it.

## Pyodide/WebAssembly {: #pyodide}

Pyodide is offered as an experimental feature in cibuildwheel.

### System requirements

Pyodide builds require a Linux or macOS machine.

### Specifying a pyodide build

You must target pyodide with `--platform pyodide` (or use `--only` on the identifier).

### Choosing a Pyodide version {: #pyodide-choosing-a-version}

It is also possible to target a specific Pyodide version by setting the [`pyodide-version`](options.md#pyodide-version) option to the desired version. Users are responsible for setting an appropriate Pyodide version according to the `pyodide-build` version. A list is available in Pyodide's [cross-build environments metadata file](https://github.com/pyodide/pyodide/blob/main/pyodide-cross-build-environments.json), which can be viewed more easily by installing `pyodide-build` from PyPI and using `pyodide xbuildenv search --all` to see a compatibility table.

If there are pre-releases available for a newer Python version, the `pyodide-prerelease` [`enable`](options.md#enable) can be used to include pre-release versions.

### Running tests

Currently, it's recommended to run tests using a `python -m` entrypoint, rather than a command line entrypoint, or a shell script. This is because custom entrypoints have some issues in the Pyodide virtual environment. For example, `pytest` may not work as a command line entrypoint, but will work as a `python -m pytest` entrypoint.

## iOS {: #ios}

### System requirements

You must be building on a macOS machine, with Xcode installed. The Xcode installation must have an iOS SDK available, with all license agreements agreed to by the user. To check if an iOS SDK is available, open the Xcode settings panel, and check the Platforms tab. This will also ensure that license agreements have been acknowledged.

Building iOS wheels also requires a working macOS Python installation. See the notes on [macOS builds](#macos) for details about configuration of the macOS environment.

### Specifying an iOS build

iOS is effectively 2 platforms - physical devices, and simulators. While the API for these two platforms are identical, the ABI is not compatible, even when dealing with a device and simulator with the same CPU architecture. For this reason, the architecture specification for iOS builds includes *both* the CPU architecture *and* the ABI that is being targeted. There are three possible values for architecture on iOS; the values match those used by `sys.implementation._multiarch` when running on iOS (with hyphens replaced with underscores, matching wheel filename normalization):

* `arm64_iphoneos` (for physical iOS devices);
* `arm64_iphonesimulator` (for iOS simulators running on Apple Silicon macOS machines); and
* `x64_64_iphonesimulator` (for iOS simulators running on Intel macOS machines).

By default, cibuildwheel will build all wheels for the CPU architecture of the build machine. You can build all wheels for all architectures by specifying `--archs all`.

If you need to specify different compilation flags or other properties on a per-ABI or per-CPU basis, you can use [configuration overrides](configuration.md#overrides) with a `select` clause that targets the specific ABI or architecture. For example, consider the following example:

```toml
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

The environment used to run builds does not inherit the full user environment - in particular, `PATH` is deliberately re-written. This is because UNIX C tooling doesn't do a great job differentiating between "macOS ARM64" and "iOS ARM64" binaries. If (for example) Homebrew is on the path when compilation commands are invoked, it's easy for a macOS version of a library to be linked into the iOS binary, rendering it unusable on iOS. To prevent this, iOS builds always force `PATH` to a "known minimal" path, that includes only the bare system utilities, and the iOS compiler toolchain.

If your project requires additional tools to build (such as `cmake`, `ninja`, or `rustc`), those tools must be explicitly declared as cross-build tools using [`xbuild-tools`](options.md#xbuild-tools). *Any* tool used by the build process must be included in the `xbuild-tools` list, not just tools that cibuildwheel will invoke directly. For example, if your build script invokes `cmake`, and the `cmake` script invokes `magick` to perform some image transformations, both `cmake` and `magick` must be included in your cross-build tools list.

### Tests

If tests have been configured, the test suite will be executed on the simulator matching the architecture of the build machine - that is, if you're building on an ARM64 macOS machine, the ARM64 wheel will be tested on an ARM64 simulator. It is not possible to use cibuildwheel to test wheels on other simulators, or on physical devices.

The iOS test environment can't support running shell scripts, so the [`test-command`](options.md#test-command) value must be specified as if it were a command line being passed to `python -m ...`. In addition, the project must use [`test-sources`](options.md#test-sources) to specify the minimum subset of files that should be copied to the test environment. This is because the test must be run "on device", and the simulator device will not have access to the local project directory.

The test process uses the same testbed used by CPython itself to run the CPython test suite. It is an Xcode project that has been configured to have a single Xcode "XCUnit" test - the result of which reports the success or failure of running `python -m <test-command>`.
