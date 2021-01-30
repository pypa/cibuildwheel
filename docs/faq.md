---
title: Tips and tricks
---

### Troubleshooting

If your wheel didn't compile, check the list below for some debugging tips.

- A mistake in your config. To quickly test your config without doing a git push and waiting for your code to build on CI, you can test the Linux build in a Docker container. On Mac or Linux, with Docker running, try `cibuildwheel --platform linux`. You'll have to bring your config into the current environment first.

- Missing dependency. You might need to install something on the build machine. You can do this in `.travis.yml`, `appveyor.yml`, or `.circleci/config.yml`, with apt-get, brew or choco. Given how the Linux build works, you'll need to use the [`CIBW_BEFORE_BUILD`](options.md#before-build) option.

- Windows: missing C feature. The Windows C compiler doesn't support C language features invented after 1990, so you'll have to backport your C code to C90. For me, this mostly involved putting my variable declarations at the top of the function like an animal.

- MacOS: calling cibuildwheel from a python3 script and getting a `ModuleNotFoundError`? Due to a [bug](https://bugs.python.org/issue22490) in CPython, you'll need to [unset the `__PYVENV_LAUNCHER__` variable](https://github.com/joerick/cibuildwheel/issues/133#issuecomment-478288597) before activating a venv.

### Linux builds on Docker

Linux wheels are built in the [`manylinux` docker images](https://github.com/pypa/manylinux) to provide binary compatible wheels on Linux, according to [PEP 571](https://www.python.org/dev/peps/pep-0571/). Because of this, when building with `cibuildwheel` on Linux, a few things should be taken into account:

- Programs and libraries cannot be installed on the Travis CI Ubuntu host with `apt-get`, but can be installed inside of the Docker image using `yum` or manually. The same goes for environment variables that are potentially needed to customize the wheel building. `cibuildwheel` supports this by providing the `CIBW_ENVIRONMENT` and `CIBW_BEFORE_BUILD` options to setup the build environment inside the running Docker image. See [the options docs](options.md#build-environment) for details on these options.

- The project directory is mounted in the running Docker instance as `/project`, the output directory for the wheels as `/output`. In general, this is handled transparently by `cibuildwheel`. For a more finegrained level of control however, the root of the host file system is mounted as `/host`, allowing for example to access shared files, caches, etc. on the host file system.  Note that this is not available on CircleCI due to their Docker policies.

- Alternative dockers images can be specified with the `CIBW_MANYLINUX_X86_64_IMAGE`, `CIBW_MANYLINUX_I686_IMAGE`, and `CIBW_MANYLINUX_PYPY_X86_64_IMAGE` options to allow for a custom, preconfigured build environment for the Linux builds. See [options](options.md#manylinux-image) for more details.

### Building non-native architectures using emulation  {: #emulation}

cibuildwheel supports building non-native architectures on Linux, via
emulation through the binfmt_misc kernel feature. The easiest way to use this
is via the [docker/setup-qemu-action][setup-qemu-action] on Github Actions or
[tonistiigi/binfmt][binfmt].

[setup-qemu-action]: https://github.com/docker/setup-qemu-action
[binfmt]: https://hub.docker.com/r/tonistiigi/binfmt

Check out the following config for an example of how to set it up on Github
Actions. Once QEMU is set up and registered, you just need to set the
`CIBW_ARCHS_LINUX` environment variable (or use the `--archs` option on
Linux), and the other architectures are emulated automatically.

> .github/workflows/build.yml
```yaml
{% include "../examples/github-with-qemu.yml" %}
```

### Building Apple Silicon wheels on Intel {: #apple-silicon}

`cibuildwheel` supports cross-compiling `universal2` and `arm64` wheels on `x86_64` runners.

These wheels are not built by default, but can be enabled by setting the [`CIBW_ARCHS_MACOS` option](options.md#archs) to `x86_64 arm64 universal2`. Cross-compilation is provided by the Xcode toolchain.

!!! important
    When cross-compiling on Intel, it is not possible to test `arm64` and the `arm64` part of a `universal2` wheel.

    `cibuildwheel` will raise a warning to notify you of this - these warnings be be silenced by skipping testing on these platforms: `CIBW_TEST_SKIP: *_arm64 *_universal2:arm64`.

Hopefully, this is a temporary situation. Once we have widely available Apple Silicon CI runners, we can build and test `arm64` and `universal2` wheels more natively. That's why `universal2` wheels are not yet built by default, and require opt-in by setting `CIBW_ARCHS_MACOS`.

!!! note
    Your runner image needs Xcode Command Line Tools 12.2 or later to build `universal2` and `arm64`.

    So far, only CPython 3.9 supports `universal2` and `arm64` wheels.

Here's an example Github Actions workflow with a job that builds for Apple Silicon:

> .github/workflows/build_macos.yml
```yml
{% include "../examples/github-apple-silicon.yml" %}
```

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

### 'No module named XYZ' errors after running cibuildwheel on macOS

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

### 'ImportError: DLL load failed: The specific module could not be found' error on Windows

Visual Studio and MSVC link the compiled binary wheels to the Microsoft Visual C++ Runtime. Normally, these are included with Python, but when compiling with a newer version of Visual Studio, it is possible users will run into problems on systems that do not have these runtime libraries installed. The solution is to ask users to download the corresponding Visual C++ Redistributable from the [Microsoft website](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) and install it. Since a Python installation normally includes these VC++ Redistributable files for [the version of the MSVC compiler used to compile Python](https://wiki.python.org/moin/WindowsCompilers), this is typically only a problem when compiling a Python 2.7 C extension with a newer compiler, e.g. to support a modern C++ standard (see [the section on modern C++ standards for Python 2.7](cpp_standards.md#windows-and-python-27) for more details).

Additionally, Visual Studio 2019 started linking to an even newer DLL, `VCRUNTIME140_1.dll`, besides the `VCRUNTIME140.dll` that is included with recent Python versions (starting from Python 3.5; see [here](https://wiki.python.org/moin/WindowsCompilers) for more details on the corresponding Visual Studio & MSVC versions used to compile the different Python versions). To avoid this extra dependency on `VCRUNTIME140_1.dll`, the [`/d2FH4-` flag](https://devblogs.microsoft.com/cppblog/making-cpp-exception-handling-smaller-x64/) can be added to the MSVC invocations (check out [this issue](https://github.com/joerick/cibuildwheel/issues/423) for details and references).

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


### Automatic updates {: #automatic-updates}

Selecting a moving target (like the latest release) is generally a bad idea in CI. If something breaks, you can't tell whether it was your code or an upstream update that caused the breakage, and in a worse-case scenario, it could occur during a release.
There are two suggested methods for keeping cibuildwheel up to date that instead involve scheduled pull requests using GitHub's dependabot.

#### Option 1: GitHub Action

If you use GitHub Actions for builds, you can use cibuildwheel as an action:

```yaml
uses: joerick/cibuildwheel@v1.8.0
```

This is a composite step that just runs cibuildwheel using pipx. You can set command-line options as `with:` parameters, and use `env:` as normal.

Then, your `dependabot.yml` file could look like this:

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    ignore:
      # Optional: Official actions have moving tags like v1;
      # if you use those, you don't need updates.
      - dependency-name: "actions/*"
```

#### Option 2: Requirement files

The second option, and the only one that supports other CI systems, is using a `requirements-*.txt` file. The file should have a distinct name and have only one entry:

```bash
# requirements-cibw.txt
cibuildwheel==1.8.0
```

Then your install step would have `python -m pip install -r requirements-cibw.txt` in it. Your `dependabot.yml` file could look like this:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
```

This will also try to update other pins in all requirement files, so be sure you want to do that. The only control you have over the files used is via the directory option.
