cibuildwheel
============

[Documentation](cibuildwheel.readthedocs.org) [![PyPI](https://img.shields.io/pypi/v/cibuildwheel.svg)](https://pypi.python.org/pypi/cibuildwheel) [![Build Status](https://travis-ci.org/joerick/cibuildwheel.svg?branch=master)](https://travis-ci.org/joerick/cibuildwheel) [![Build status](https://ci.appveyor.com/api/projects/status/wbsgxshp05tt1tif/branch/master?svg=true)](https://ci.appveyor.com/project/joerick/cibuildwheel/branch/master) [![CircleCI](https://circleci.com/gh/joerick/cibuildwheel.svg?style=svg)](https://circleci.com/gh/joerick/cibuildwheel)

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

Example setup
-------------

To build manylinux and macOS wheels on Travis CI, and upload them to PyPI whenever you tag a version, you could use this `.travis.yml`:

```yaml
language: python

matrix:
  include:
    - sudo: required
      services:
        - docker
      env: PIP=pip
    - os: osx
      language: generic
      env: PIP=pip2

env:
  global:
    - TWINE_USERNAME=joerick
      # Note: TWINE_PASSWORD is set in Travis settings

script:
  - $PIP install cibuildwheel==0.12.0
  - cibuildwheel --output-dir wheelhouse
  - |
    if [[ $TRAVIS_TAG ]]; then
      python -m pip install twine
      python -m twine upload wheelhouse/*.whl
    fi
```

Working examples
----------------

Here are some repos that use cibuildwheel. 

- [pyinstrument_cext](https://github.com/joerick/pyinstrument_cext)
- [websockets](https://github.com/aaugustin/websockets)
- [Parselmouth](https://github.com/YannickJadoul/Parselmouth)
- [python-admesh](https://github.com/admesh/python-admesh)
- [pybase64](https://github.com/mayeut/pybase64)
- [KDEpy](https://github.com/tommyod/KDEpy)
- [AutoPy](https://github.com/autopilot-rs/autopy)
- [apriltags2-ethz](https://github.com/safijari/apriltags2_ethz)
- [TgCrypto](https://github.com/pyrogram/tgcrypto)
- [Twisted](https://github.com/twisted/twisted)

> Add repo here! Send a PR.

Legal note
----------

Since `cibuildwheel` runs the wheel through delocate or auditwheel, it might automatically bundle dynamically linked libraries from the build machine. 

It helps ensure that the library can run without any dependencies outside of the pip toolchain.

This is similar to static linking, so it might have some licence implications. Check the license for any code you're pulling in to make sure that's allowed.

Maintainers
-----------

- Joe Rickerby [@joerick](https://github.com/joerick)
- Tomas Garcia [@tgarc](https://github.com/tgarc)
- Yannick Jadoul [@YannickJadoul](https://github.com/YannickJadoul)
- Matthieu Darbois [@mayeut](https://github.com/mayeut)

Credits
-------

`cibuildwheel` stands on the shoulders of giants. 

- ⭐️ @matthew-brett for [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild) and [matthew-brett/delocate](http://github.com/matthew-brett/delocate)
- @PyPA for the manylinux Docker images [pypa/manylinux](https://github.com/pypa/manylinux)
- @ogrisel for [wheelhouse-uploader](https://github.com/ogrisel/wheelhouse-uploader) and `run_with_env.cmd`

Massive props also to-

- @zfrenchee for [help debugging many issues](https://github.com/joerick/cibuildwheel/issues/2)
- @lelit for some great bug reports and [contributions](https://github.com/joerick/cibuildwheel/pull/73)
- @mayeut for a [phenomenal PR](https://github.com/joerick/cibuildwheel/pull/71) patching Python itself for better compatibility!

See also
--------

If you'd like to keep wheel building separate from the package itself, check out [astrofrog/autowheel](https://github.com/astrofrog/autowheel). It builds packages using cibuildwheel from source distributions on PyPI.

If `cibuildwheel` is too limited for your needs, consider [matthew-brett/multibuild](http://github.com/matthew-brett/multibuild). `multibuild` is a toolbox for building a wheel on various platforms. It can do a lot more than this project - it's used to build SciPy!
