---
title: Changelog
---

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
  images, set your [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)
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
  and [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image)
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
  build using the old manylinux1 image using the [manylinux image](https://cibuildwheel.readthedocs.io/en/stable/options/#manylinux-image) option.
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
  [cibuildwheel-azure-example](https://github.com/pypa/cibuildwheel-azure-example)
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

<script>
  // undo the scrollTop that the theme did on this page, as there are loads
  // of toc entries and it's disorientating.
  window.addEventListener('DOMContentLoaded', function() {
    $('.wy-nav-side').scrollTop(0)
  })
</script>
