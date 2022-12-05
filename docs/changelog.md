---
title: Changelog
---

# Changelog

### v2.11.3

_5 Dec 2022_

- ✨ Improves the 'build options' log output that's printed at the start of each run (#1352)
- ✨ Added a friendly error message to a common misconfiguration of the `CIBW_TEST_COMMAND` option - not specifying path using the `{project}` placeholder (#1336)
- 🛠 The GitHub Action now uses Powershell on Windows to avoid occasional incompabilities with bash (#1346)

### v2.11.2

_26 October 2022_

- 🛠 Updates CPython 3.11 to 3.11.0 - final release (#1327)
- 🛠 Simplify the default macOS repair command (#1322)
- 🛠 Fix the default `MACOSX_DEPLOYMENT_TARGET` on arm64 (#1312)
- 🛠 Hide irrelevant pip warnings on linux (#1311)
- 🐛 Fix a bug that caused the stdout and stderr of commands in containers to be in the wrong order Previously, stdout could appear after stderr. (#1324)
- 📚 Added [a FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#macos-building-cpython-38-wheels-on-arm64) describing how to perform native builds of CPython 3.8 wheels on Apple Silicon. (#1323)
- 📚 Other docs improvements

### v2.11.1

_13 October 2022_

- 🛠 Updates to the latest manylinux images, and updates CPython 3.10 to 3.10.8.

### v2.11.0

_13 October 2022_

- 🌟 Adds support for cross-compiling Windows ARM64 wheels. To use this feature, add `ARM64` to the [CIBW_ARCHS](https://cibuildwheel.readthedocs.io/en/stable/options/#archs) option on a Windows Intel runner. (#1144)
- ✨ Adds support for building Linux aarch64 wheels on Circle CI. (#1307)
- ✨ Adds support for building Windows wheels on Gitlab CI. (#1295)
- ✨ Adds support for building Linux aarch64 wheels under emulation on Gitlab CI. (#1295)
- ✨ Adds the ability to test `cp38-macosx_arm64` wheels on a native arm64 runner. To do this, you'll need to preinstall the (experimental) [universal2 version of CPython 3.8](https://www.python.org/ftp/python/3.8.10/python-3.8.10-macos11.pkg) on your arm64 runner before invoking cibuildwheel. Note: it is not recommended to build x86_64 wheels with this setup, your wheels will have limited compatibility wrt macOS versions. (#1283)
- 🛠 Improved error messages when using custom Docker images and Python cannot be found at the correct path. (#1298)
- 📚 Sample configs for Azure Pipelines and Travis CI updated (#1296)
- 📚 Other docs improvements - including more information about using Homebrew for build dependencies (#1290)

### v2.10.2

_25 September 2022_

- 🐛 Fix a bug that caused `win32` identifiers to fail when used with `--only`. (#1282)
- 🐛 Fix computation of `auto`/`auto64`/`auto32` archs when targeting a different platform to the one that you're running cibuildwheel on. (#1266)
- 📚 Fix an mistake in the 'how it works' diagram. (#1274)

### v2.10.1

_18 September 2022_

- 🐛 Fix a bug that stopped environment variables specified in TOML from being expanded. (#1273)

### v2.10.0

_13 September 2022_

- 🌟 Adds support for [building wheels on Cirrus CI](https://cibuildwheel.readthedocs.io/en/stable/setup/#cirrus-ci). This is exciting for us, as it's the first public CI platform that natively supports macOS Apple Silicon (aka. M1, `arm64`) runners. As such, it's the first platform that you can natively build _and test_ macOS `arm64` wheels. It also has native Linux ARM (aarch64) runners, for fast, native builds there. (#1191)
- 🌟 Adds support for running cibuildwheel on Apple Silicon machines. For a while, we've supported cross-compilation of Apple Silicon wheels on `x86_64`, but now that we have Cirrus CI we can run our test suite and officially support running cibuildwheel on `arm64`. (#1191)
- ✨ Adds the `--only` [command line option](https://cibuildwheel.readthedocs.io/en/stable/options/#command-line), to specify a single build to run. Previously, it could be cumbersome to set all the build selection options to target a specific build - for example, you might have to run something like `CIBW_BUILD=cp39-manylinux_x86_64 cibuildwheel --platform linux --archs x86_64`. The new `--only` option overrides all the build selection options to simplify running a single build, which now looks like `cibuildwheel --only cp39-manylinux_x86_64`. (#1098)
- ✨ Adds the [`CIBW_CONFIG_SETTINGS`](https://cibuildwheel.readthedocs.io/en/stable/options/#config-settings) option, so you can pass arguments to your package's build backend (#1244)
- 🛠 Updates the CPython 3.11 version to the latest release candidate - v3.11.0rc2. (#1265)
- 🐛 Fix a bug that can cause a RecursionError on Windows when building from an sdist. (#1253)
- 🛠 Add support for the s390x architecture on manylinux_2_28 (#1255)

### v2.9.0

_11 August 2022_

- 🌟 CPython 3.11 wheels are now built by default - without the CIBW_PRERELEASE_PYTHONS flag. It's time to build and upload these wheels to PyPI! This release includes CPython 3.11.0rc1, which is guaranteed to be ABI compatible with the final release. (#1226)
- ⚠️ Removed support for running cibuildwheel in Python 3.6. Python 3.6 is EOL. However, cibuildwheel continues to build CPython 3.6 wheels for the moment. (#1175)
- ✨ Improved error messages when misspelling TOML options, suggesting close matches (#1205)
- 🛠 When running on Apple Silicon (so far, an unsupported mode of operation), cibuildwheel no longer builds universal2 wheels by default - just arm64. See [#1204](https://github.com/pypa/cibuildwheel/issues/1204) for discussion. We hope to release official support for native builds on Apple Silicon soon! (#1217)

### v2.8.1

_18 July 2022_

- 🐛 Fix a bug when building CPython 3.8 wheels on an Apple Silicon machine where testing would always fail. cibuildwheel will no longer attempt to test the arm64 part of CPython 3.8 wheels because we use the x86_64 installer of CPython 3.8 due to its macOS system version backward-compatibility. See [#1169](https://github.com/pypa/cibuildwheel/pull/1169) for more details. (#1171)
- 🛠 Update the prerelease CPython 3.11 to 3.11.0b4. (#1180)
- 🛠 The GitHub Action will ensure a compatible version of Python is installed on the runner (#1114)
- 📚 A few docs improvements

### v2.8.0

_5 July 2022_

- ✨ You can now run cibuildwheel on Podman, as an alternate container engine to Docker (which remains the default). This is useful in environments where a Docker daemon isn't available, for example, it can be run inside a Docker container, or without root access. To use Podman, set the [`CIBW_CONTAINER_ENGINE`](https://cibuildwheel.readthedocs.io/en/stable/options/#container-engine) option. (#966)
- ✨ Adds support for building `py3-none-{platform}` wheels. This works the same as ABI3 - wheels won't be rebuilt, but tests will still be run across all selected versions of Python.

    These wheels contain native extension code, but don't use the Python APIs. Typically, they're bridged to Python using a FFI module like [ctypes](https://docs.python.org/3/library/ctypes.html) or [cffi](https://cffi.readthedocs.io/en/latest/). Because they don't use Python ABI, the wheels are more compatible - they work across many Python versions.

    Check out this [example ctypes project](https://github.com/joerick/python-ctypes-package-sample) to see an example of how it works. (#1151)

- 🛠 cibuildwheel will now error if multiple builds in a single run produce the same wheel filename, as this indicates a misconfiguration. (#1152)
- 📚 A few docs improvements and updates to keep things up-to-date.

### v2.7.0

_17 June 2022_

- 🌟 Added support for the new `manylinux_2_28` images. These new images are based on AlmaLinux, the community-driven successor to CentOS, unlike manylinux_2_24, which was based on Debian. To build on these images, set your [`CIBW_MANYLINUX_*_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image) option to `manylinux_2_28`. (#1026)
- 🐛 Fix a bug where tests were not being run on CPython 3.11 (when CIBW_PRERELEASE_PYTHONS was set) (#1138)
- ✨ You can now build Linux wheels on Windows, as long as you have Docker installed and set to 'Linux containers' (#1117)
- 🐛 Fix a bug on macOS that caused cibuildwheel to crash trying to overwrite a previously-built wheel of the same name. (#1129)

### v2.6.1

_7 June 2022_

- 🛠 Update the prerelease CPython 3.11 to 3.11.0b3

### v2.6.0

_25 May 2022_

- 🌟 Added the ability to test building wheels on CPython 3.11! Because CPython 3.11 is in beta, these wheels should not be distributed, because they might not be compatible with the final release, but it's available to build for testing purposes. Use the flag [`--prerelease-pythons` or `CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons) to test. This version of cibuildwheel includes CPython 3.11.0b1. (#1109)
- 📚 Added an interactive diagram showing how cibuildwheel works to the [docs](https://cibuildwheel.readthedocs.io/en/stable/#how-it-works) (#1100)

### v2.5.0

_29 April 2022_

- ✨ Added support for building ABI3 wheels. cibuildwheel will now recognise when an ABI3 wheel was produced, and skip subsequent build steps where the previously built wheel is compatible. Tests still will run on all selected versions of Python, using the ABI3 wheel. Check [this entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#abi3) in the docs for more info. (#1091)
- ✨ You can now build wheels directly from sdist archives, in addition to source directories. Just call cibuildwheel with an sdist argument on the command line, like `cibuildwheel mypackage-1.0.0.tar.gz`. For more details, check the [`--help` output](https://cibuildwheel.readthedocs.io/en/stable/options/#command-line) (#1096)
- 🐛 Fix a bug where cibuildwheel would crash when no builds are selected and `--allow-empty` is passed (#1086)
- 🐛 Workaround a permissions issue on Linux relating to newer versions of git and setuptools_scm (#1095)
- 📚 Minor docs improvements

### v2.4.0

_2 April 2022_

- ✨ cibuildwheel now supports running locally on Windows and macOS (as well as Linux). On macOS, you'll have to install the versions of Pythons that you want to use from Python.org, and cibuildwheel will use them. On Windows, cibuildwheel will install it's own versions of Python. Check out [the documentation](https://cibuildwheel.readthedocs.io/en/stable/setup/#local) for instructions. (#974)
- ✨ Added support for building PyPy 3.9 wheels. (#1031)
- ✨ Listing at the end of the build now displays the size of each wheel (#975)
- 🐛 Workaround a connection timeout bug on Travis CI ppc64le runners (#906)
- 🐛 Fix an encoding error when reading setup.py in the wrong encoding (#977)
- 🛠 Setuptools updated to 61.3.0, including experimental support for reading config from pyproject.toml(PEP 621). This could change the behaviour of your build if you have a pyproject.toml with a `[project]` table, because that takes precedence over setup.py and setup.cfg. Check out the [setuptools docs](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html) and the [project metadata specification](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/) for more info.
- 🛠 Many other dependency updates.
- 📚 Minor docs improvements

### v2.3.1

_14 December 2021_

- 🐛 Setting pip options like `PIP_USE_DEPRECATED` in `CIBW_ENVIRONMENT` no longer adversely affects cibuildwheel's ability to set up a Python environment (#956)
- 📚 Docs fixes and improvements

### v2.3.0

_26 November 2021_

- 📈 cibuildwheel now defaults to manylinux2014 image for linux builds, rather than manylinux2010. If you want to stick with manylinux2010, it's simple to set this using [the image options](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image). (#926)
- ✨ You can now pass environment variables from the host machine into the Docker container during a Linux build. Check out [the docs for `CIBW_ENVIRONMENT_PASS_LINUX `](https://cibuildwheel.readthedocs.io/en/latest/options/#environment-pass) for the details. (#914)
- ✨ Added support for building PyPy 3.8 wheels. (#881)
- ✨ Added support for building Windows arm64 CPython wheels on a Windows arm64 runner. We can't test this in CI yet, so for now, this is experimental. (#920)
- 📚 Improved the deployment documentation (#911)
- 🛠 Changed the escaping behaviour inside cibuildwheel's  option placeholders e.g. `{project}` in `before_build` or `{dest_dir}` in `repair_wheel_command`. This allows bash syntax like `${SOME_VAR}` to passthrough without being interpreted as a placeholder by cibuildwheel. See [this section](https://cibuildwheel.readthedocs.io/en/stable/options/#placeholders) in the docs for more info. (#889)
- 🛠 Pip updated to 21.3, meaning it now defaults to in-tree builds again. If this causes an issue with your project, setting environment variable `PIP_USE_DEPRECATED=out-of-tree-build` is available as a temporary flag to restore the old behaviour. However, be aware that this flag will probably be removed soon. (#881)
- 🐛 You can now access the current Python interpreter using `python3` within a build on Windows (#917)

### v2.2.2

_26 October 2021_

- 🐛 Fix bug in the GitHub Action step causing a syntax error (#895)

### v2.2.1

_26 October 2021_

- 🛠 Added a `config-file` option on the GitHub Action to specify something other than pyproject.toml in your GitHub Workflow file. (#883)
- 🐛 Fix missing resources in sdist and released wheel on PyPI. We've also made some internal changes to our release processes to make them more reliable. (#893, #894)

### v2.2.0

_22 October 2021_

- 🌟 Added support for [musllinux](https://www.python.org/dev/peps/pep-0656/). Support for this new wheel format lets projects build wheels for Linux distributions that use [musl libc](https://musl.libc.org/), notably, [Alpine](https://alpinelinux.org/) Docker containers. (#768)

  Musllinux builds are enabled by default. If you're not ready to build musllinux, add `*-musllinux_*` to your [`CIBW_SKIP`/`skip`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-skip) option. Or, you might have to make some changes to your options - to simplify that process, you can use...

- 🌟 TOML option overrides! This provides much greater flexibility in configuration via pyproject.toml. (#854)

  You can now set build options for any subset of your builds using a match pattern. So, for example, you can customise CPython 3.8 builds with an override on `cp38-*` or musllinux builds by selecting `*musllinux*`. Check out [the docs](https://cibuildwheel.readthedocs.io/en/latest/options/#overrides) for more info on the specifics.

- 🛠 Added support for building PyPy wheels on macOS 11 CI runners. (#875)

- 🛠 Setting an empty string for the [`CIBW_*_IMAGE`](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image) option will now fallthrough to the config file or cibuildwheel's default, rather than causing an error. This makes the option easier to use in CI build matricies. (#829)

- 🛠 Support for TOML 1.0 when reading config files, via the `tomli` package. (#876)

<sup>Note: This version is not available on PyPI due to some missing resources in the release files. Please use a later version instead.</sup>

### v2.1.3

_6 October 2021_

- 🛠 Updated CPython 3.10 to the 3.10.0 final release

### v2.1.2

_14 September 2021_

- 🛠 Updated CPython 3.10 to 3.10.0rc2
- 📚 Multiple docs updates
- 🐛 Improved warnings when built binaries are bundled into the container on Linux. (#807)

### v2.1.1

_7 August 2021_

- ✨ Corresponding with the release of CPython 3.10.0rc1, which is ABI stable, cibuildwheel now builds CPython 3.10 by default - without the CIBW_PRERELEASE_PYTHONS flag.

<sup>Note: v2.1.0 was a bad release, it was yanked from PyPI.</sup>

### v2.0.1

_25 July 2021_

- 📚 Docs improvements (#767)
- 🛠 Dependency updates, including delocate 0.9.0.

### v2.0.0 🎉

_16 July 2021_

- 🌟 You can now configure cibuildwheel options inside your project's `pyproject.toml`! Environment variables still work of course. Check out the [documentation](https://cibuildwheel.readthedocs.io/en/stable/options/#setting-options) for more info.
- 🌟 Added support for building wheels with [build](https://github.com/pypa/build), as well as pip. This feature is controlled with the [`CIBW_BUILD_FRONTEND`](https://cibuildwheel.readthedocs.io/en/stable/options/#build-frontend) option.
- 🌟 Added the ability to test building wheels on CPython 3.10! Because CPython 3.10 is in beta, these wheels should not be distributed, because they might not be compatible with the final release, but it's available to build for testing purposes. Use the flag [`--prerelease-pythons` or `CIBW_PRERELEASE_PYTHONS`](https://cibuildwheel.readthedocs.io/en/stable/options/#prerelease-pythons) to test. (#675) This version of cibuildwheel includes CPython 3.10.0b4.
- ⚠️ **Removed support for building Python 2.7 and Python 3.5 wheels**, for both CPython and PyPy. If you still need to build on these versions, please use the latest v1.x version. (#596)
- ✨ Added the ability to build CPython 3.8 wheels for Apple Silicon. (#704)
- 🛠 Update to the latest build dependencies, including Auditwheel 4. (#633)
- 🛠 Use the unified pypa/manylinux images to build PyPy (#671)
- 🐛 Numerous bug fixes & docs improvements

### v1.12.0

_22 June 2021_

- ✨ Adds support building macOS universal2/arm64 wheels on Python 3.8.

### v1.11.1

_28 May 2021_

- ✨ cibuildwheel is now part of the PyPA!
- 📚 Minor docs changes, fixing links related to the above transition
- 🛠 Update manylinux pins to the last version containing Python 2.7 and 3.5. (#674)

### v1.11.0

_1 May 2021_

- 📚 Lots of docs improvements! (#650, #623, #616, #609, #606)
- 🐛 Fix nuget "Package is not found" error on Windows. (#653)
- ⚠️ cibuildwheel will no longer build Windows 2.7 wheels, unless you specify a custom toolchain using `DISTUTILS_USE_SDK=1` and `MSSdk=1`. This is because Microsoft have stopped distributing Visual C++ Compiler for Python 2.7. See [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#windows-and-python-27) for more details. (#649)
- 🐛 Fix crash on Windows due to missing `which` command (#641).

### v1.10.0

_22 Feb 2021_

- ✨ Added `manylinux_2_24` support. To use these new Debian-based manylinux
  images, set your [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image)
  options to `manylinux_2_24`.
- 🛠 On macOS, we now set `MACOSX_DEPLOYMENT_TARGET` in before running
  `CIBW_BEFORE_ALL`. This is useful when using `CIBW_BEFORE_ALL` to build a
  shared library.
- 🛠 An empty `CIBW_BUILD` option is now the same as being unset i.e, `*`.
  This makes some build matrix configuration easier. (#588)
- 📚 Neatened up documentation - added tabs to a few places (#576), fixed some
  formatting issues.

### v1.9.0

_5 February 2021_

- 🌟 Added support for Apple Silicon wheels on macOS! You can now
  cross-compile `universal2` and `arm64` wheels on your existing macOS Intel
  runners, by setting
  [CIBW_ARCHS_MACOS](https://cibuildwheel.readthedocs.io/en/stable/options/#archs).
  Xcode 12.2 or later is required, but you don't need macOS 11.0 - you can
  still build on macOS 10.15. See
  [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#apple-silicon)
  for more information. (#484)
- 🌟 Added auto-detection of your package's Python compatibility, via declared
   [`requires-python`](https://www.python.org/dev/peps/pep-0621/#requires-python)
  in your `pyproject.toml`, or
  [`python_requires`](https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires)
  in `setup.cfg` or `setup.py`. If your project has these set, cibuildwheel
  will automatically skip builds on versions of Python that your package
  doesn't support. Hopefully this makes the first-run experience of
  cibuildwheel a bit easier. If you need to override this for any reason,
  look at [`CIBW_PROJECT_REQUIRES_PYTHON`](https://cibuildwheel.readthedocs.io/en/stable/options/#requires-python).
  (#536)
- 🌟 cibuildwheel can now be invoked as a native GitHub Action! You can now
  invoke cibuildwheel in a GHA build step like:

  ```yaml
  - name: Build wheels
    uses: pypa/cibuildwheel@version # e.g. v1.9.0
    with:
      output-dir: wheelhouse
    # env:
    #   CIBW_SOME_OPTION: value
  ```

  This saves a bit of boilerplate, and you can [use Dependabot to keep the
  pinned version up-to-date](https://cibuildwheel.readthedocs.io/en/stable/faq/#automatic-updates).

- ✨ Added `auto64` and `auto32` shortcuts to the
  [CIBW_ARCHS](https://cibuildwheel.readthedocs.io/en/stable/options/#archs)
  option. (#553)
- ✨ cibuildwheel now prints a list of the wheels built at the end of each
  run. (#570)
- 📚 Lots of minor docs improvements.

### 1.8.0

_22 January 2021_

- 🌟 Added support for emulated builds! You can now build manylinux wheels on
  ARM64`aarch64`, as well as `ppc64le` and 's390x'. To build under emulation,
  register QEMU via binfmt_misc and set the
  [`CIBW_ARCHS_LINUX`](https://cibuildwheel.readthedocs.io/en/stable/options/#archs)
  option to the architectures you want to run. See
  [this FAQ entry](https://cibuildwheel.readthedocs.io/en/stable/faq/#emulation)
  for more information. (#482)
- ✨ Added `CIBW_TEST_SKIP` option. This allows you to choose certain builds
  whose tests you'd like to skip. This might be useful when running a slow
  test suite under emulation, for example. (#537)
- ✨ Added `curly-{brace,bracket,paren}` style globbing to `CIBW_BUILD` and
  `CIBW_SKIP`. This gives more expressivity, letting you do things like
  `CIBW_BUILD=cp39-manylinux_{aarch64,ppc64le}`. (#527)
- 🛠 cibuildwheel will now exit with an error if it's called with options that
  skip all builds on a platform. This feature can be disabled by adding
  `--allow-empty` on the command line. (#545)

### 1.7.4

_2 January 2021_

- 🐛 Fix the PyPy virtualenv patch to work on macOS 10.14 (#506)

### 1.7.3

_1 January 2021_

- 🛠 Added a patch for Pypy to ensure header files are available for building
  in a virtualenv. (#502)
- 🛠 Some preparatory work towards using cibuildwheel as a GitHub Action.
  Check out
  [the FAQ](https://cibuildwheel.readthedocs.io/en/stable/faq/#option-1-github-action)
  for information on how to use it. We'll be fully updating the docs to this
  approach in a subsequent release (#494)

### 1.7.2

_21 December 2020_

- 🛠 Update dependencies, notably wheel==0.36.2 and pip==20.3.3, and CPython to
  their latest bugfix releases (#489)
- 📚 Switch to a GitHub example in the README (#479)
- 📚 Create Working Examples table, with many projects that use cibuildwheel (#474)
- 📚 Import Working Examples table and Changelog to docs

### 1.7.1

_3 December 2020_

- 🛠 Update manylinux2010 image to resolve issues with 'yum' repositories
  (#472)

### 1.7.0

_26 November 2020_

- ✨ New logging format, that uses 'fold groups' in CI services that support
  it. (#458)
- 🛠 Update PyPy to 7.3.3 (#460)
- 🐛 Fix a bug where CIBW_BEFORE_ALL runs with a very old version of Python on
  Linux. (#464)

### 1.6.4

_31 October 2020_

- 🐛 Fix crash on Appveyor during nuget install due to old system CA
  certificates. We now use certifi's CA certs to download files. (#455)

### 1.6.3

_12 October 2020_

- 🐛 Fix missing SSL certificates on macOS (#447)
- 🛠 Update OpenSSL Python 3.5 patch to 1.1.1h on macOS (#449)

### 1.6.2

_9 October 2020_

- ✨ Python 3.9 updated to the final release version - v3.9.0 (#440)
- 🛠 Pypy updated to v7.3.2, adding alpha support for Python 3.7 (#430)

### 1.6.1

_20 September 2020_

- 🛠 Add PPC64LE manylinux image supporting Python 3.9. (#436)
- 📚 Add project URLs to PyPI listing (#428)

### 1.6.0

_9 September 2020_

- 🌟 Add Python 3.9 support! This initial support uses release candidate
  builds. You can start publishing wheels for Python 3.9 now, ahead of
  the official release. (#382)

  Minor note - if you're building PPC64LE wheels, the manylinux image pinned
  by this version is
  [still on Python 3.9b3](https://github.com/pypa/manylinux/issues/758), not a
  release candidate. We'd advise holding off on distributing 3.9 ppc64le wheels
  until a subsequent version of cibuildwheel.

- 🌟 Add Gitlab CI support. Gitlab CI can now build Linux wheels, using
  cibuildwheel. (#419)
- 🐛 Fix a bug that causes pyproject.toml dependencies to fail to install on
  Windows (#420)
- 📚 Added some information about Windows VC++ runtimes and how they relate
  to wheels.

### 1.5.5

_22 July 2020_

- 🐛 Fix a bug that would cause command substitutions in CIBW_ENVIRONMENT to
  produce no output on Linux (#411)
- 🐛 Fix regression (introduced in 1.5.3) which caused BEFORE_BUILD and
  BEFORE_ALL to be executed in the wrong directory (#410)

### 1.5.4

_19 June 2020_

- 🐛 Fix a bug that would cause command substitutions in CIBW_ENVIRONMENT
  variables to not interpret quotes in commands correctly (#406, #408)

### 1.5.3

_19 July 2020_

- 🛠 Update CPython 3.8 to 3.8.3 (#405)
- 🛠 Internal refactoring of Linux build, to move control flow into Python (#386)

### 1.5.2

_8 July 2020_

- 🐛 Fix an issue on Windows where pyproject.toml would cause an error when
  some requirements formats were used. (#401)
- 🛠 Update CPython 3.7 to 3.7.8 (#394)

### 1.5.1

_25 June 2020_

- 🐛 Fix "OSError: [WinError 17] The system cannot move the file to a different
  disk drive" on GitHub Actions (#388, #389)

### 1.5.0

_24 June 2020_

- 🌟 Add [`CIBW_BEFORE_ALL`](https://cibuildwheel.readthedocs.io/en/stable/options/#before-all)
  option, which lets you run a command on the build machine before any wheels
  are built. This is especially useful when building on Linux, to `make`
  something external to Python, or to `yum install` a dependency. (#342)
- ✨ Added support for projects using pyproject.toml instead of setup.py
  (#360, #358)
- ✨ Added workaround to allow Python 3.5 on Windows to pull dependencies from
  pyproject.toml. (#358)
- 📚 Improved GitHub Actions examples and docs (#354, #362)
- 🐛 Ensure pip wheel uses the specified package, and doesn't build a wheel
  from PyPI (#369)
- 🛠 Internal changes: using pathlib.Path, precommit hooks, testing
  improvements.

### 1.4.2

_25 May 2020_

- 🛠 Dependency updates, including CPython 3.8.3 & manylinux images.
- 🛠 Lots of internal updates - type annotations and checking using mypy, and
  a new integration testing system.
- ⚠️ Removed support for *running* cibuildwheel using Python 3.5. cibuildwheel
  will continue to build Python 3.5 wheels until EOL.

### 1.4.1

_4 May 2020_

- 🐛 Fix a bug causing programs running inside the i686 manylinux images to
  think they were running x86_64 and target the wrong architecture. (#336,
  #338)

### 1.4.0

_2 May 2020_

- 🌟 Deterministic builds. cibuildwheel now locks the versions of the tools it
  uses. This means that pinning your version of cibuildwheel pins the versions
  of pip, setuptools, manylinux etc. that are used under the hood. This should
  make things more reliable. But note that we don't control the entire build
  environment on macOS and Windows, where the version of Xcode and Visual
  Studio can still effect things.

  This can be controlled using the [CIBW_DEPENDENCY_VERSIONS](https://cibuildwheel.readthedocs.io/en/stable/options/#dependency-versions)
  and [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image)
  options - if you always want to use the latest toolchain, you can still do
  that, or you can specify your own pip constraints file and manylinux image.
  (#256)

- ✨ Added `package_dir` command line option, meaning we now support building
  a package that lives in a subdirectory and pulls in files from the wider
  project. See [the `package_dir` option help](https://cibuildwheel.readthedocs.io/en/stable/options/#command-line-options)
  for more information.

  Note that this change makes the working directory (where you call
  cibuildwheel from) relevant on Linux, as it's considered the 'project' and
  will be copied into the Docker container. If your builds are slower on this
  version, that's likely the reason. `cd` to your project and then call
  `cibuildwheel` from there. (#319, #295)

- 🛠 On macOS, we make `MACOSX_DEPLOYMENT_TARGET` default to `10.9` if it's
  not set. This should make things more consistent between Python versions.
- 🛠 Dependency updates - CPython 3.7.7, CPython 2.7.18, Pypy 7.3.1.

### 1.3.0

_12 March 2020_

- 🌟 Add support for building on GitHub Actions! Check out the
  [docs](https://cibuildwheel.readthedocs.io/en/stable/setup/#github-actions)
  for information on how to set it up. (#194)
- ✨ Add the `CIBW_BEFORE_TEST` option, which lets you run a command to
  prepare the environment before your tests are run. (#242)

### 1.2.0

_8 March 2020_

- 🌟 Add support for building PyPy wheels, across Manylinux, macOS, and
  Windows. (#185)
- 🌟 Added the ability to build ARM64 (aarch64), ppc64le, and s390x wheels,
  using manylinux2014 and Travis CI. (#273)
- ✨ You can now build macOS wheels on Appveyor. (#230)
- 🛠 Changed default macOS minimum target to 10.9, from 10.6. This allows the
  use of more modern C++ libraries, among other things. (#156)
- 🛠 Stop building universal binaries on macOS. We now only build x86_64
  wheels on macOS. (#220)
- ✨ Allow chaining of commands using `&&` and `||` on Windows inside
  CIBW_BEFORE_BUILD and CIBW_TEST_COMMAND. (#293)
- 🛠 Improved error reporting for failed Cython builds due to stale .so files
  (#263)
- 🛠 Update CPython from 3.7.5 to 3.7.6 and from 3.8.0 to 3.8.2 on Mac/Windows
- 🛠 Improved error messages when a bad config breaks cibuildwheel's PATH
  variable. (#264)
- ⚠️ Removed support for *running* cibuildwheel on Python 2.7. cibuildwheel
  will continue to build Python 2.7 wheels for a little while. (#265)

### 1.1.0

_7 December 2019_

- 🌟 Add support for building manylinux2014 wheels. To use, set
  `CIBW_MANYLINUX_X86_64_IMAGE` and CIBW_MANYLINUX_I686_IMAGE to
  `manylinux2014`.
- ✨ Add support for [Linux on Appveyor](https://www.appveyor.com/blog/2018/03/06/appveyor-for-linux/) (#204, #207)
- ✨ Add `CIBW_REPAIR_WHEEL_COMMAND` env variable, for changing how
  `auditwheel` or `delocate` are invoked, or testing an equivalent on
  Windows. (#211)
- 📚 Added some travis example configs - these are available in /examples. (#228)

### 1.0.0

_10 November 2019_

- 🌟 Add support for building Python 3.8 wheels! (#180)
- 🌟 Add support for building manylinux2010 wheels. cibuildwheel will now
  build using the manylinux2010 images by default. If your project is still
  manylinux1 compatible, you should get both manylinux1 and manylinux2010
  wheels - you can upload both to PyPI. If you always require manylinux1 wheels, you can
  build using the old manylinux1 image using the [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#linux-image) option.
  (#155)
- 📚 Documentation is now on its [own mini-site](https://cibuildwheel.readthedocs.io),
   rather than on the README (#169)
- ✨ Add support for building Windows wheels on Travis CI. (#160)
- 🛠 If you set `CIBW_TEST_COMMAND`, your tests now run in a virtualenv. (#164)
- 🛠 Windows now uses Python as installed by nuget, rather than the versions
  installed by the various CI providers. (#180)
- 🛠 Update Python from 2.7.16 to 2.7.17 and 3.7.4 to 3.7.5 on macOS (#171)
- ⚠️ Removed support for Python 3.4 (#168)

### 0.12.0

_29 September 2019_

- ✨ Add CIBW_TEST_EXTRAS option, to allow testing using extra_require
  options. For example, set `CIBW_TEST_EXTRAS=test,qt` to make the wheel
  installed with `pip install <wheel_file>[test,qt]`
- 🛠 Update Python from 3.7.2 to 3.7.4 on macOS
- 🛠 Update OpenSSL patch to 1.0.2t on macOS

### 0.11.1

_28 May 2019_

- 🐛 Fix missing file in the release tarball, that was causing problems with
  Windows builds (#141)

### 0.11.0

_26 May 2019_

- 🌟 Add support for building on Azure pipelines! This lets you build all
  Linux, Mac and Windows wheels on one service, so it promises to be the
  easiest to set up! Check out the quickstart in the docs, or
  [cibuildwheel-azure-example](https://github.com/joerick/cibuildwheel-azure-example)
  for an example project. (#126, #132)
- 🛠 Internal change - the end-to-end test projects format was updated, so we
  can more precisely assert what should be produced for each one. (#136, #137).

### 0.10.2

_10 March 2019_

- 🛠 Revert temporary fix in macOS, that was working around a bug in pip 19 (#129)
- 🛠 Update Python to 2.7.16 on macOS
- 🛠 Update OpenSSL patch to 1.0.2r on macOS

### 0.10.1

_3 February 2019_

- 🐛 Fix build stalling on macOS (that was introduced in pip 19) (#122)
- 🐛 Fix "AttributeError: 'Popen' object has no attribute 'args'" on Python 2.7 for Linux builds (#108)
- 🛠 Update Python from 3.6.7, 3.7.1 to 3.6.8, 3.7.2 on macOS
- 🛠 Update openssl patch from 1.0.2p to 1.0.2q on macOS
- 🛠 Sorting build options dict items when printing preamble (#114)

### 0.10.0

_23 September 2018_

- 🌟 Add `CIBW_BUILD` option, for specifying which specific builds to perform (#101)
- 🌟 Add support for building Mac and Linux on CircleCI (#91, #97)
- 🛠 Improved support for building universal wheels (#95)
- 🛠 Ensure log output is unbuffered and therefore in the correct order (#92)
- 🛠 Improved error reporting for errors that occur inside a package's setup.py (#88)
- ⚠️ Removed support for Python 3.3 on Windows.

### 0.9.4

_29 July 2018_

- 🛠 CIBW_TEST_COMMAND now runs in a shell on Mac (as well as Linux) (#81)

### 0.9.3

_10 July 2018_

- 🛠 Update to Python 3.6.6 on macOS (#82)
- ✨ Add support for building Python 3.7 wheels on Windows (#76)
- ⚠️ Deprecated support for Python 3.3 on Windows.

### 0.9.2

_1 July 2018_

- 🛠  Update Python 3.7.0rc1 to 3.7.0 on macOS (#79)

### 0.9.1

_18 June 2018_

- 🛠 Removed the need to use `{python}` and `{pip}` in `CIBW_BEFORE_BUILD` statements, by ensuring the correct version is always on the path at `python` and `pip` instead. (#60)
- 🛠 We now patch the _ssl module on Python 3.4 and 3.5 so these versions can still make SSL web requests using TLS 1.2 while building. (#71)

### 0.9.0

_18 June 2018_

- ✨ Add support for Python 3.7 (#73)

### 0.8.0

_4 May 2018_

- ⚠️ Drop support for Python 3.3 on Linux (#67)
- 🐛 Fix TLS by updating setuptools (#69)

### 0.7.1

_2 April 2017_

- 🐛 macOS: Fix Pip bugs resulting from PyPI TLS 1.2 enforcement
- 🐛 macOS: Fix brew Python3 version problems in the CI

### 0.7.0

_7 January 2018_

- ✨ You can now specify a custom docker image using the `CIBW_MANYLINUX1_X86_64_IMAGE` and `CIBW_MANYLINUX1_I686_IMAGE` options. (#46)
- 🐛 Fixed a bug where cibuildwheel would download and build a package from PyPI(!) instead of building the package on the local machine. (#51)

### 0.6.0

_9 October 2017_

- ✨ On the Linux build, the host filesystem is now accessible via `/host` (#36)
- 🐛 Fixed a bug where setup.py scripts would run the wrong version of Python when running subprocesses on Linux (#35)

### 0.5.1

_10 September 2017_

- 🐛 Fixed a couple of bugs on Python 3.
- ✨ Added experimental support for Mac builds on [Bitrise.io](https://www.bitrise.io)

### 0.5.0

_7 September 2017_

- ✨ `CIBW_ENVIRONMENT` added. You can now set environment variables for each build, even within the Docker container on Linux. This is a big one! (#21)
- ✨ `CIBW_BEFORE_BUILD` now runs in a system shell on all platforms. You can now do things like `CIBW_BEFORE_BUILD="cmd1 && cmd2"`. (#32)

### 0.4.1

_14 August 2017_

- 🐛 Fixed a bug on Windows where subprocess' output was hidden (#23)
- 🐛 Fixed a bug on AppVeyor where logs would appear in the wrong order due to output buffering (#24, thanks @YannickJadoul!)

### 0.4.0

_23 July 2017_

- 🐛 Fixed a bug that was increasing the build time by building the wheel twice. This was a problem for large projects that have a long build time. If you're upgrading and you need the old behaviour, use `CIBW_BEFORE_BUILD={pip} install .`, or install exactly the dependencies you need in `CIBW_BEFORE_BUILD`. See #18.

### 0.3.0

_27 June 2017_

- ⚠️ Removed Python 2.6 support on Linux (#12)

### 0.2.1

_11 June 2017_

- 🛠 Changed the build process to install the package before building the wheel - this allows direct dependencies to be installed first (#9, thanks @tgarc!)
- ✨ Added Python 3 support for the main process, for systems where Python 3 is the default (#8, thanks @tgarc).

### 0.2.0

_13 April 2017_

- ✨ Added `CIBW_SKIP` option, letting users explicitly skip a build
- ✨ Added `CIBW_BEFORE_BUILD` option, letting users run a shell command before the build starts

### 0.1.3

_31 March 2017_

- 🌟 First public release!

<style>

/* improve list formatting to help separate items */

.rst-content li {
  margin-bottom: 12px;
}
.rst-content .section ol li>p:only-child, .rst-content .section ol li>p:only-child:last-child, .rst-content .section ul li>p:only-child, .rst-content .section ul li>p:only-child:last-child, .rst-content .toctree-wrapper ol li>p:only-child, .rst-content .toctree-wrapper ol li>p:only-child:last-child, .rst-content .toctree-wrapper ul li>p:only-child, .rst-content .toctree-wrapper ul li>p:only-child:last-child, .rst-content section ol li>p:only-child, .rst-content section ol li>p:only-child:last-child, .rst-content section ul li>p:only-child, .rst-content section ul li>p:only-child:last-child {
  margin-bottom: 12px
}
</style>

<script>
  // undo the scrollTop that the theme did on this page, as there are loads
  // of toc entries and it's disorientating.
  window.addEventListener('DOMContentLoaded', function() {
    $('.wy-nav-side').scrollTop(0)
  })
</script>
