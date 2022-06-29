---
title: Tips and tricks
---

## Tips

### Linux builds on Docker

Linux wheels are built in the [`manylinux`/`musllinux` docker images](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 600](https://www.python.org/dev/peps/pep-0600/) / [PEP 656](https://www.python.org/dev/peps/pep-0656/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:

-   Programs and libraries are not installed on the CI runner host, but rather should be installed inside of the Docker image - using `yum` for `manylinux2010` or `manylinux2014`, `apt-get` for `manylinux_2_24` and `apk` for `musllinux_1_1`, or manually. The same goes for environment variables that are potentially needed to customize the wheel building.

    `cibuildwheel` supports this by providing the [`CIBW_ENVIRONMENT`](options.md#environment) and [`CIBW_BEFORE_ALL`](options.md#before-all) options to setup the build environment inside the running Docker image.

-   The project directory is mounted in the running Docker instance as `/project`, the output directory for the wheels as `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that `/host` is not available on CircleCI due to their Docker policies.

-   Alternative Docker images can be specified with the `CIBW_MANYLINUX_*_IMAGE`/`CIBW_MUSLLINUX_*_IMAGE` options to allow for a custom, preconfigured build environment for the Linux builds. See [options](options.md#linux-image) for more details.

### Building macOS wheels for Apple Silicon {: #apple-silicon}

`cibuildwheel` supports cross-compiling `universal2` and `arm64` wheels on `x86_64` runners. With the introduction of Apple Silicon, you now have several choices for wheels for Python 3.8+:

#### `x86_64`

The traditional wheel for Apple, loads on Intel machines, and on
Apple Silicon when running Python under Rosetta 2 emulation.

Due to a change in naming, Pip 20.3+ (or an installer using packaging 20.5+)
is required to install a binary wheel on macOS Big Sur.

#### `arm64`

The native wheel for macOS on Apple Silicon.

Requires Pip 20.3+ (or packaging 20.5+) to install.

#### `universal2`

This wheel contains both architectures, causing it to be up to twice the
size (data files do not get doubled, only compiled code). It requires
Pip 20.3 (Packaging 20.6+) to load on Intel, and Pip 21.0.1 (Packaging 20.9+)
to load on Apple Silicon.

!!! note
    The dual-architecture `universal2` has a few benefits, but a key benefit
    to a universal wheel is that a user can bundle these wheels into an
    application and ship a single binary.

    However, if you have a large library, then you might prefer to ship
    the two single-arch wheels instead - `x86_64` and `arm64`. In rare cases,
    you might want to build all three, but in that case, pip will not download
    the universal wheels, because it prefers the most specific wheel
    available.

Generally speaking, because Pip 20.3 is required for the `universal2` wheel,
most packages should provide both `x86_64` and `universal2` wheels for now.
Once Pip 20.3+ is common on macOS, then it should be possible to ship only the
`universal2` wheel.

**Apple Silicon wheels are not built by default**, but can be enabled by adding extra archs to the [`CIBW_ARCHS_MACOS` option](options.md#archs) - e.g. `x86_64 arm64 universal2`. Cross-compilation is provided by the Xcode toolchain.

!!! important
    When cross-compiling on Intel, it is not possible to test `arm64` and the `arm64` part of a `universal2` wheel.

    `cibuildwheel` will raise a warning to notify you of this - these warnings be be silenced by skipping testing on these platforms: `CIBW_TEST_SKIP: *_arm64 *_universal2:arm64`.

Hopefully, cross-compilation is a temporary situation. Once we have widely
available Apple Silicon CI runners, we can build and test `arm64` and
`universal2` wheels natively. That's why `universal2` wheels are not yet built
by default, and require opt-in by setting `CIBW_ARCHS_MACOS`.

!!! note
    Your runner needs Xcode Command Line Tools 12.2 or later to build `universal2` or `arm64`.

    Only CPython 3.8 and newer support `universal2` and `arm64` wheels.

Here's an example GitHub Actions workflow with a job that builds for Apple Silicon:

> .github/workflows/build_macos.yml

```yml
{% include "../examples/github-apple-silicon.yml" %}
```

### Building non-native architectures using emulation  {: #emulation}

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

### Building packages with optional C extensions

`cibuildwheel` defines the environment variable `CIBUILDWHEEL` to the value `1` allowing projects for which the C extension is optional to make it mandatory when building wheels.

An easy way to do it in Python 3 is through the `optional` named argument of `Extension` constructor in your `setup.py`:

```python
myextension = Extension(
    "myextension",
    ["myextension.c"],
    optional=os.environ.get('CIBUILDWHEEL', '0') != '1',
)
```

### Automatic updates {: #automatic-updates}

Selecting a moving target (like the latest release) is generally a bad idea in CI. If something breaks, you can't tell whether it was your code or an upstream update that caused the breakage, and in a worse-case scenario, it could occur during a release.
There are two suggested methods for keeping cibuildwheel up to date that instead involve scheduled pull requests using GitHub's dependabot.

#### Option 1: GitHub Action

If you use GitHub Actions for builds, you can use cibuildwheel as an action:

```yaml
uses: pypa/cibuildwheel@v2.7.0
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
cibuildwheel==2.7.0
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
    "wheel",
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

See the [cibuildwheel version 1 docs](https://cibuildwheel.readthedocs.io/en/1.x/) for information about building Python 2.7 or PyPy2 wheels. There are lots of tricks and workaround there that are no longer required for Python 3 in cibuildwheel 2.

## Troubleshooting

If your wheel didn't compile, you might have a mistake in your config.

To quickly test your config without doing a git push and waiting for your code to build on CI, you can [test the Linux build in a local Docker container](setup.md#local).

### Missing dependencies

You might need to install something on the build machine. You can do this with apt/yum, brew or choco, using the [`CIBW_BEFORE_ALL`](options.md#before-all) option. Or, for a Python dependency, consider [adding it to pyproject.toml](#cibw-options-alternatives-deps).

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

Solutions to this vary, but the simplest is to install tools immediately before they're used:

```bash
python3 -m pip install cibuildwheel
python3 -m cibuildwheel --output-dir wheelhouse
python3 -m pip install twine
python3 -m twine upload wheelhouse/*.whl
```

### macOS: Passing DYLD_LIBRARY_PATH to delocate

macOS has built-in [System Integrity protections](https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html) which limits the use of `DYLD_LIBRARY_PATH` and `LD_LIBRARY_PATH` so that it does not automatically pass to children processes. This means if you set `DYLD_LIBRARY_PATH` before running cibuildwheel, or even set it in `CIBW_ENVIRONMENT`, it will be stripped out of the environment before delocate is called.

To work around this, use a different environment variable such as `REPAIR_LIBRARY_PATH` to store the library path, and set `DYLD_LIBRARY_PATH` in [`CIBW_REPAIR_WHEEL_COMMAND_MACOS`](https://cibuildwheel.readthedocs.io/en/stable/options/#repair-wheel-command), like this:

!!! tab examples "Environment variables"

    ```yaml
    CIBW_REPAIR_WHEEL_COMMAND_MACOS: >
        DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-listdeps {wheel} &&
        DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}
    ```

!!! tab examples "pyproject.toml"

    ```toml
    [tool.cibuildwheel.macos]
    repair-wheel-command = [
        "DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-listdeps {wheel}",
        "DYLD_LIBRARY_PATH=$REPAIR_LIBRARY_PATH delocate-wheel --require-archs {delocate_archs} -w {dest_dir} {wheel}"
    ]
    ```

See [#816](https://github.com/pypa/cibuildwheel/issues/816), thanks to @phoerious for reporting.

### Windows: 'ImportError: DLL load failed: The specific module could not be found'

Visual Studio and MSVC link the compiled binary wheels to the Microsoft Visual C++ Runtime. Normally, these are included with Python, but when compiling with a newer version of Visual Studio, it is possible users will run into problems on systems that do not have these runtime libraries installed. The solution is to ask users to download the corresponding Visual C++ Redistributable from the [Microsoft website](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) and install it. Since a Python installation normally includes these VC++ Redistributable files for [the version of the MSVC compiler used to compile Python](https://wiki.python.org/moin/WindowsCompilers), this is typically only a problem when compiling a Python C extension with a newer compiler.

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

To investigate the dependencies of a C extension (i.e., the `.pyd` file, a DLL in disguise) on Windows, [Dependency Walker](http://www.dependencywalker.com/) is a great tool.
