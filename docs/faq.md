---
title: Tips and tricks
---

# Tips and tricks

## Tips

### Linux builds in containers

Linux wheels are built in [`manylinux`/`musllinux` containers](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 600](https://www.python.org/dev/peps/pep-0600/) / [PEP 656](https://www.python.org/dev/peps/pep-0656/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:

-   Programs and libraries are not installed on the CI runner host, but rather should be installed inside the container - using `yum` for `manylinux2010` or `manylinux2014`, `apt-get` for `manylinux_2_24`, `dnf` for `manylinux_2_28` and `apk` for `musllinux_1_1` or `musllinux_1_2`, or manually. The same goes for environment variables that are potentially needed to customize the wheel building.

    `cibuildwheel` supports this by providing the [`CIBW_ENVIRONMENT`](options.md#environment) and [`CIBW_BEFORE_ALL`](options.md#before-all) options to setup the build environment inside the running container.

-   The project directory is copied into the container as `/project`, the output directory for the wheels to be copied out is `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that `/host` is not available on CircleCI and GitLab CI due to their Docker policies.

-   Alternative Docker images can be specified with the `CIBW_MANYLINUX_*_IMAGE`/`CIBW_MUSLLINUX_*_IMAGE` options to allow for a custom, preconfigured build environment for the Linux builds. See [options](options.md#linux-image) for more details.

### Building macOS wheels for Apple Silicon {: #apple-silicon}

`cibuildwheel` supports both native builds and cross-compiling between `arm64` (Apple Silicon) and `x86_64` (Intel) architectures, including the cross-compatible `universal2` format.

#### Overview of Mac architectures

You have several choices for wheels for Python 3.8+:

##### `x86_64`

The traditional wheel for Apple, loads on Intel machines, and on
Apple Silicon when running Python under Rosetta 2 emulation.

Due to a change in naming, Pip 20.3+ (or an installer using packaging 20.5+)
is required to install a binary wheel on macOS Big Sur.

##### `arm64`

The native wheel for macOS on Apple Silicon.

Requires Pip 20.3+ (or packaging 20.5+) to install.

##### `universal2`

This wheel contains both architectures, causing it to be up to twice the
size (data files do not get doubled, only compiled code). It requires
Pip 20.3 (Packaging 20.6+) to load on Intel, and Pip 21.0.1 (Packaging 20.9+)
to load on Apple Silicon.

The dual-architecture `universal2` has a few benefits, but a key benefit
to a universal wheel is that a user can bundle these wheels into an
application and ship a single binary.

However, if you have a large library, then you might prefer to ship
the two single-arch wheels instead - `x86_64` and `arm64`. In rare cases,
you might want to build all three, but in that case, pip will not download
the universal wheels, because it prefers the most specific wheel
available.

#### What to provide?

Generally speaking, because Pip 20.3 is required for the `universal2` wheel,
most packages should provide both `x86_64` and one of `universal2`/`arm64`
wheels. When Pip 20.3+ is common on macOS, then it might be possible to ship
only the `universal2` wheel.

Opinions vary on which of arch-specific or `universal2` wheels are best - some packagers prefer `universal2` because it's one wheel for all Mac users, so simpler, and easier to build into apps for downstream users. However, because they contain code for both architectures, their file size is larger, meaning they consume more disk space and bandwidth, and are harder to build for some projects.

See [GitHub issue 1333](https://github.com/pypa/cibuildwheel/issues/1333) for more discussion.

#### How?

It's easiest to build `x86_64` wheels on `x86_64` runners, and `arm64` wheels on `arm64` runners.

On GitHub Actions, `macos-14` runners are `arm64`, and `macos-13` runners are `x86_64`. So all you need to do is ensure both are in your build matrix.

#### Cross-compiling

If your CI provider doesn't offer arm64 runners yet, or you want to create `universal2`, you'll have to cross-compile. Cross-compilation can be enabled by adding extra archs to the [`CIBW_ARCHS_MACOS` option](options.md#archs) - e.g. `CIBW_ARCHS_MACOS="x86_64 universal2"`. Cross-compilation is provided by Xcode toolchain v12.2+.

Regarding testing,

- On an arm64 runner, it is possible to test x86_64 wheels and both parts of a universal2 wheel using Rosetta 2 emulation.
- On an x86_64 runner, arm64 code can be compiled but it can't be tested. `cibuildwheel` will raise a warning to notify you of this - these warnings can be silenced by skipping testing on these platforms: `CIBW_TEST_SKIP: "*_arm64 *_universal2:arm64"`.

!!! note
    If your project uses **Poetry** as a build backend, cross-compiling on macOS [does not currently work](https://github.com/python-poetry/poetry/issues/7107). In some cases arm64 wheels can be built but their tags will be incorrect, with the platform tag showing `x86_64` instead of `arm64`.

    As a workaround, the tag can be fixed before running delocate to repair the wheel. The [`wheel tags`](https://wheel.readthedocs.io/en/stable/reference/wheel_tags.html) command is ideal for this. See [this workflow](https://gist.github.com/anderssonjohan/49f07e33fc5cb2420515a8ac76dc0c95#file-build-pendulum-wheels-yml-L39-L53) for an example usage of `wheel tags`.

### Building Linux wheels for non-native archs using emulation  {: #emulation}

cibuildwheel supports building non-native architectures on Linux, via
emulation through the binfmt_misc kernel feature. The easiest way to use this
is via the [docker/setup-qemu-action][setup-qemu-action] on GitHub Actions or
[tonistiigi/binfmt][binfmt].

[setup-qemu-action]: https://github.com/docker/setup-qemu-action
[binfmt]: https://hub.docker.com/r/tonistiigi/binfmt

Check out the following config for an example of how to set it up on GitHub
Actions. Once QEMU is set up and registered, you just need to set the
`CIBW_ARCHS_LINUX` environment variable (or use the `--archs` option on
Linux), and the other architectures are emulated automatically.

> .github/workflows/build.yml

```yaml
{% include "../examples/github-with-qemu.yml" %}
```

### Building CPython ABI3 wheels (Limited API) {: #abi3}

The CPython Limited API is a subset of the Python C Extension API that's declared to be forward-compatible, meaning you can compile wheels for one version of Python, and they'll be compatible with future versions. Wheels that use the Limited API are known as ABI3 wheels.

To create a package that builds ABI3 wheels, you'll need to configure your build backend to compile libraries correctly create wheels with the right tags. [Check this repo](https://github.com/joerick/python-abi3-package-sample) for an example of how to do this with setuptools.

You could also consider running [abi3audit](https://github.com/trailofbits/abi3audit) against the produced wheels in order to check for abi3 violations or inconsistencies. You can run it alongside the default in your [CIBW_REPAIR_WHEEL_COMMAND](options.md#repair-wheel-command).

### Packages with optional C extensions {: #optional-extensions}

`cibuildwheel` defines the environment variable `CIBUILDWHEEL` to the value `1` allowing projects for which the C extension is optional to make it mandatory when building wheels.

An easy way to do it in Python 3 is through the `optional` named argument of `Extension` constructor in your `setup.py`:

```python
myextension = Extension(
    "myextension",
    ["myextension.c"],
    optional=os.environ.get('CIBUILDWHEEL', '0') != '1',
)
```

### Automatic updates using Dependabot {: #automatic-updates}

Selecting a moving target (like the latest release) is generally a bad idea in CI. If something breaks, you can't tell whether it was your code or an upstream update that caused the breakage, and in a worse-case scenario, it could occur during a release.

There are two suggested methods for keeping cibuildwheel up to date that instead involve scheduled pull requests using GitHub's Dependabot.

#### Option 1: GitHub Action

If you use GitHub Actions for builds, you can use cibuildwheel as an action:

```yaml
uses: pypa/cibuildwheel@v2.18.1
```

This is a composite step that just runs cibuildwheel using pipx. You can set command-line options as `with:` parameters, and use `env:` as normal.

Then, your `.github/dependabot.yml` file could look like this:

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

#### Option 2: Requirement files

The second option, and the only one that supports other CI systems, is using a `requirements-*.txt` file. The file should have a distinct name and have only one entry:

```bash
# requirements-cibw.txt
cibuildwheel==2.18.1
```

Then your install step would have `python -m pip install -r requirements-cibw.txt` in it. Your `.github/dependabot.yml` file could look like this:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
```

This will also try to update other pins in all requirement files, so be sure you want to do that. The only control you have over the files used is via the directory option.


### Alternatives to cibuildwheel options {: #cibw-options-alternatives}

cibuildwheel provides lots of opportunities to configure the build
environment. However, you  might consider adding this build configuration into
the package itself - in general, this is preferred, because users of your
package 'sdist' will also benefit.

#### Missing build dependencies {: #cibw-options-alternatives-deps}

If your build needs Python dependencies, rather than using `CIBW_BEFORE_BUILD`, it's best to add these to the
[`build-system.requires`](https://www.python.org/dev/peps/pep-0518/#build-system-table)
section of your pyproject.toml. For example, if your project requires Cython
to build, your pyproject.toml might include a section like this:

```toml
[build-system]
requires = [
    "setuptools>=42",
    "Cython",
]

build-backend = "setuptools.build_meta"
```

#### Actions you need to perform before building

You might need to run some other commands before building, like running a
script that performs codegen or downloading some data that's not stored in
your source tree.

Rather than using `CIBW_BEFORE_ALL` or `CIBW_BEFORE_BUILD`, you could incorporate
these steps into your package's build process. For example, if you're using
setuptools, you can add steps to your package's `setup.py` using a structure
like this:

```python
import subprocess
import setuptools
import setuptools.command.build_py


class BuildPyCommand(setuptools.command.build_py.build_py):
    """Custom build command."""

    def run(self):
        # your custom build steps here
        # e.g.
        #   subprocess.run(['python', 'scripts/my_custom_script.py'], check=True)
        setuptools.command.build_py.build_py.run(self)


setuptools.setup(
    cmdclass={
        'build_py': BuildPyCommand,
    },
    # Usual setup() args.
    # ...
)
```

#### Compiler flags

Your build might need some compiler flags to be set through environment variables.
Consider incorporating these into your package, for example, in `setup.py` using [`extra_compile_args` or
`extra_link_args`](https://docs.python.org/3/distutils/setupscript.html#other-options).

### Python 2.7 / PyPy2 wheels

See the [cibuildwheel version 1 docs](https://cibuildwheel.pypa.io/en/1.x/) for information about building Python 2.7 or PyPy2 wheels. There are lots of tricks and workaround there that are no longer required for Python 3 in cibuildwheel 2.

## Troubleshooting

If your wheel didn't compile, you might have a mistake in your config.

To quickly test your config without doing a git push and waiting for your code to build on CI, you can [test the Linux build in a local Docker container](setup.md#local).

### Missing dependencies

Sometimes a build will fail due to a missing dependency.

**If the build is missing a Python package**, you should [add it to pyproject.toml](#cibw-options-alternatives-deps).

**If you need a build tool** (e.g. cmake, automake, ninja), you can install it through a package manager like apt/yum, brew or choco, using the [`CIBW_BEFORE_ALL`](options.md#before-all) option.

**If your build is linking into a native library dependency**, you can build/install that in [`CIBW_BEFORE_ALL`](options.md#before-all). However, on Linux, Mac (and Windows if you're using [delvewheel]), the library that you install will be bundled into the wheel in the [repair step]. So take care to ensure that

- the bundled library doesn't accidentally increase the minimum system requirements (such as the minimum macOS version)
- the bundled library matches the architecture of the wheel you're building when cross-compiling

This is particularly an issue on macOS, where de facto package manager Homebrew will install libraries that are compiled for the specific version of macOS that the build machine is running, rendering the wheels useless for any previous version. And brew will not install the right arch for cross compilation of Apple Silicon wheels.

For these reasons, it's strongly recommended to not use brew for native library dependencies. Instead, we recommend compiling the library yourself. If you compile in the [`CIBW_BEFORE_ALL`](options.md#before-all) step, cibuildwheel will have already set the appropriate `MACOSX_DEPLOYMENT_TARGET` env var, so the library will target the correct version of macOS.

!!! tip
    For build steps, Homebrew is still a great resource - you can [look up the build formula](https://formulae.brew.sh/) and use that as a starting point.

[delvewheel]: https://github.com/adang1345/delvewheel
[repair step]: options.md#repair-wheel-command
[Homebrew]: https://brew.sh/
[delocate]: https://github.com/matthew-brett/delocate

### Building Rust wheels

If you build Rust wheels, you need to download the Rust compilers in manylinux.
If you support 32-bit Windows, you need to add this as a potential target. You
can do this on GitHub Actions, for example, with:

```yaml
CIBW_BEFORE_ALL_LINUX: curl -sSf https://sh.rustup.rs | sh -s -- -y
CIBW_BEFORE_ALL_WINDOWS: rustup target add i686-pc-windows-msvc
CIBW_ENVIRONMENT_LINUX: "PATH=$HOME/.cargo/bin:$PATH"
```

Rust does not provide Cargo for musllinux 32-bit, so that needs to be skipped:

```toml
[tool.cibuildwheel]
skip = ["*-musllinux_i686"]
```

Also see [maturin-action](https://github.com/PyO3/maturin-action) which is optimized for Rust wheels, builds the non-Python Rust modules once, and can cross-compile (and can build 32-bit musl, for example).

### macOS: ModuleNotFoundError

Calling cibuildwheel from a python3 script and getting a `ModuleNotFoundError`? Due to a (fixed) [bug](https://bugs.python.org/issue22490) in CPython, you'll need to [unset the `__PYVENV_LAUNCHER__` variable](https://github.com/pypa/cibuildwheel/issues/133#issuecomment-478288597) before activating a venv.

### macOS: 'No module named XYZ' errors after running cibuildwheel

`cibuildwheel` on Mac installs the distributions from Python.org system-wide during its operation. This is necessary, but it can cause some confusing errors after cibuildwheel has finished.

Consider the build script:

```bash
python3 -m pip install twine cibuildwheel
python3 -m cibuildwheel --output-dir wheelhouse
python3 -m twine upload wheelhouse/*.whl
# error: no module named 'twine'
```

This doesn't work because while `cibuildwheel` was running, it installed a few new versions of 'python3', so the `python3` run on line 3 isn't the same as the `python3` that ran on line 1.

Solutions to this vary, but the simplest is to use pipx:

```bash
# most runners have pipx preinstalled, but in case you don't
python3 -m pip install pipx

pipx run cibuildwheel==2.18.1 --output-dir wheelhouse
pipx run twine upload wheelhouse/*.whl
```

### macOS: Passing DYLD_LIBRARY_PATH to delocate

macOS has built-in [System Integrity protections](https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html) which limits the use of `DYLD_LIBRARY_PATH` and `LD_LIBRARY_PATH` so that it does not automatically pass to children processes. This means if you set `DYLD_LIBRARY_PATH` before running cibuildwheel, or even set it in `CIBW_ENVIRONMENT`, it will be stripped out of the environment before delocate is called.

To work around this, use a different environment variable such as `REPAIR_LIBRARY_PATH` to store the library path, and set `DYLD_LIBRARY_PATH` in [`CIBW_REPAIR_WHEEL_COMMAND_MACOS`](https://cibuildwheel.pypa.io/en/stable/options/#repair-wheel-command), like this:

!!! tab examples "Environment variables"

    ```yaml
    CIBW_REPAIR_WHEEL_COMMAND_MACOS: >
        DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-wheel --require-archs {delocate_archs} -w {dest_dir} -v {wheel}
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.macos]
    repair-wheel-command = """\
    DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-wheel \
    --require-archs {delocate_archs} -w {dest_dir} -v {wheel}\
    """
    ```

See [#816](https://github.com/pypa/cibuildwheel/issues/816), thanks to @phoerious for reporting.

### macOS: Building CPython 3.8 wheels on arm64

If you're building on an arm64 runner, you might notice something strange about CPython 3.8 - unlike Python 3.9+, it's cross-compiled to arm64 from an x86_64 version of Python running under Rosetta emulation. This is because (despite the prevalence of arm64 versions of Python 3.8 from Apple and Homebrew) there is no officially supported Python.org installer of Python 3.8 for arm64.

This is fine for simple C extensions, but for more complicated builds on arm64 it becomes an issue.

So, if the cross-compilation is an issue for you, there is an 'experimental' installer available that's built natively for arm64.

To use this installer and perform native CPython 3.8 building, before invoking cibuildwheel, install the universal2 version of Python on your arm64 runner, something like:


```bash
curl -o /tmp/Python38.pkg https://www.python.org/ftp/python/3.8.10/python-3.8.10-macos11.pkg
sudo installer -pkg /tmp/Python38.pkg -target /
sh "/Applications/Python 3.8/Install Certificates.command"
```

Then cibuildwheel will detect that it's installed and use it instead. However, you probably don't want to build x86_64 wheels on this Python, unless you're happy with them only supporting macOS 11+.

### macOS: Library dependencies do not satisfy target MacOS

Since delocate 0.11.0 there is added verification that the library binary dependencies match the target macOS version. This is to prevent the situation where a wheel platform tag is lower than the actual minimum macOS version required by the library. To resolve this error you need to build the library to the same macOS version as the target wheel (for example using `MACOSX_DEPLOYMENT_TARGET` environment variable).
Alternatively, you could set `MACOSX_DEPLOYMENT_TARGET` in `CIBW_ENVIRONMENT` to correctly label the wheel as incompatible with older macOS versions.

This error may happen when you install a library using a package manager like Homebrew, which compiles the library for the macOS version of the build machine. This is not suitable for wheels, as the library will only work on the same macOS version as the build machine. You should compile the library yourself, or use a precompiled binary that matches the target macOS version.

### Windows: 'ImportError: DLL load failed: The specific module could not be found'

Visual Studio and MSVC link the compiled binary wheels to the Microsoft Visual C++ Runtime. Normally, the C parts of the runtime are included with Python, but the C++ components are not. When compiling modules using C++, it is possible users will run into problems on systems that do not have the full set of runtime libraries installed. The solution is to ask users to download the corresponding Visual C++ Redistributable from the [Microsoft website](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) and install it.

Additionally, Visual Studio 2019 started linking to an even newer DLL, `VCRUNTIME140_1.dll`, besides the `VCRUNTIME140.dll` that is included with recent Python versions (starting from Python 3.5; see [here](https://wiki.python.org/moin/WindowsCompilers) for more details on the corresponding Visual Studio & MSVC versions used to compile the different Python versions). To avoid this extra dependency on `VCRUNTIME140_1.dll`, the [`/d2FH4-` flag](https://devblogs.microsoft.com/cppblog/making-cpp-exception-handling-smaller-x64/) can be added to the MSVC invocations (check out [this issue](https://github.com/pypa/cibuildwheel/issues/423) for details and references). CPython 3.8.3 and all versions after it have this extra DLL, so it is only needed for 3.8 and earlier.

To add the `/d2FH4-` flag to a standard `setup.py` using `setuptools`, the `extra_compile_args` option can be used:

```python
    ext_modules=[
        Extension(
            'c_module',
            sources=['extension.c'],
            extra_compile_args=['/d2FH4-'] if sys.platform == 'win32' else []
        )
    ],
```

To investigate the dependencies of a C extension (i.e., the `.pyd` file, a DLL in disguise) on Windows, [Dependency Walker](http://www.dependencywalker.com/) is a great tool. For diagnosing a failing import, the [dlltracer](https://pypi.org/project/dlltracer/) tool may also provide additional details.

### Windows ARM64 builds {: #windows-arm64}

`cibuildwheel` supports cross-compiling `ARM64` wheels on all Windows runners, but a native ARM64 runner is required for testing. On non-native runners, tests for ARM64 wheels will be automatically skipped with a warning. Add `"*-win_arm64"` to your `CIBW_TEST_SKIP` setting to suppress the warning.

Cross-compilation on Windows relies on a supported build backend. Supported backends use an environment variable to specify their target platform (the one they are compiling native modules for, as opposed to the one they are running on), which is set in [cibuildwheels/windows.py](https://github.com/pypa/cibuildwheel/blob/main/cibuildwheel/windows.py) before building. Currently, `setuptools>=65.4.1` and `setuptools_rust` are the only supported backends.

By default, `ARM64` is not enabled when running on non-ARM64 runners. Use [`CIBW_ARCHS`](options.md#archs) to select it.
