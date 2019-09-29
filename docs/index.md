Home
====

Python wheels are great. Building them across **Mac, Linux, Windows**, on **multiple versions of Python**, is not.

`cibuildwheel` is here to help. `cibuildwheel` runs on your CI server - currently it supports Azure Pipelines, Travis CI, AppVeyor, and CircleCI - and it builds and tests your wheels across all of your platforms.

**`cibuildwheel` is in beta**. It's brand new - I'd love for you to try it and help make it better!

What does it do?
----------------

|   | macOS 10.6+ | manylinux i686 | manylinux x86_64 |  Windows 32bit | Windows 64bit |
|---|---|---|---|---|---|
| Python 2.7 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.4 | ✅ | ✅ | ✅ | ✅* | ✅* |
| Python 3.5 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.6 | ✅ | ✅ | ✅ | ✅  | ✅  |
| Python 3.7 | ✅ | ✅ | ✅ | ✅  | ✅  |

> \* Not supported on Azure Pipelines

- Builds manylinux, macOS and Windows (32 and 64bit) wheels using Azure Pipelines, Travis CI, AppVeyor, and CircleCI
- Bundles shared library dependencies on Linux and macOS through [auditwheel](https://github.com/pypa/auditwheel) and [delocate](https://github.com/matthew-brett/delocate)
- Runs the library test suite against the wheel-installed version of your library

Usage
-----

`cibuildwheel` currently works  **Travis CI** and **CircleCI** to build Linux and Mac wheels, and **AppVeyor** to build Windows wheels. **Azure Pipelines** supports all three.

|                 | Linux | macOS | Windows |
|-----------------|-------|-------|---------|
| Azure Pipelines | ✅    | ✅    | ✅      |
| Travis CI       | ✅    | ✅    |         |
| AppVeyor        |       |       | ✅      |
| CircleCI        | ✅    | ✅    |         |

`cibuildwheel` is not intended to run on your development machine. It will try to install packages globally; this is no good. Travis CI, CircleCI, and AppVeyor run their builds in isolated environments, so are ideal for this kind of script.
