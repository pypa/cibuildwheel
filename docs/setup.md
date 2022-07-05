---
title: 'Setup'
---

# Run cibuildwheel locally (optional) {: #local}

Before getting to CI setup, it can be convenient to test cibuildwheel
locally to quickly iterate and track down issues without even touching CI.

Install cibuildwheel and run a build like this:

!!! tab "Linux"

    Using [pipx](https://github.com/pypa/pipx):
    ```sh
    pipx run cibuildwheel --platform linux
    ```

    Or,
    ```sh
    pip install cibuildwheel
    cibuildwheel --platform linux
    ```

!!! tab "macOS"

    Using [pipx](https://github.com/pypa/pipx):
    ```sh
    pipx run cibuildwheel --platform macos
    ```

    Or,
    ```sh
    pip install cibuildwheel
    cibuildwheel --platform macos
    ```


!!! tab "Windows"

    Using [pipx](https://github.com/pypa/pipx):
    ```bat
    pipx run cibuildwheel --platform windows
    ```

    Or,
    ```bat
    pip install cibuildwheel
    cibuildwheel --platform windows
    ```

You should see the builds taking place. You can experiment with options using environment variables or pyproject.toml.

!!! tab "Environment variables"

    cibuildwheel will read config from the environment. Syntax varies, depending on your shell:

    > POSIX shell (Linux/macOS)

    ```sh
    # run a command to set up the build system
    export CIBW_BEFORE_ALL='apt install libpng-dev'

    cibuildwheel --platform linux
    ```

    > CMD (Windows)

    ```bat
    set CIBW_BEFORE_ALL='apt install libpng-dev'

    cibuildwheel --platform linux
    ```

!!! tab "pyproject.toml"

    If you write your options into [`pyproject.toml`](options.md#configuration-file), you can work on your options locally, and they'll be automatically picked up when running in CI.

    > pyproject.toml

    ```
    [tool.cibuildwheel]
    before-all = "apt install libpng-dev"
    ```

    Then invoke cibuildwheel, like:

    ```console
    cibuildwheel --platform linux
    ```

## Linux builds

If you've got [Docker](https://www.docker.com/products/docker-desktop) installed on
your development machine, you can run a Linux build.

!!! tip
    You can run the Linux build on any platform. Even Windows can run
    Linux containers these days, but there are a few  hoops to jump
    through. Check [this document](https://docs.microsoft.com/en-us/virtualization/windowscontainers/quick-start/quick-start-windows-10-linux)
    for more info.

Because the builds are happening in manylinux Docker containers,
they're perfectly reproducible.

The only side effect to your system will be docker images being pulled.

## macOS / Windows builds

Pre-requisite: you need to have native build tools installed.

Because the builds are happening without full isolation, there might be some
differences compared to CI builds (Xcode version, Visual Studio version,
OS version, local files, ...) that might prevent you from finding an issue only
seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be
reused for future builds. The folder used for caching is system/user dependent and is
reported in the printed preamble of each run (e.g. "Cache folder: /Users/Matt/Library/Caches/cibuildwheel").

You can override the cache folder using the ``CIBW_CACHE_PATH`` environment variable.

!!! warning
    cibuildwheel uses official python.org macOS installers for CPython but
    those can only be installed globally.

    In order not to mess with your system, cibuildwheel won't install those if they are
    missing. Instead, it will error out with a message to let you install the missing
    CPython:

    ```console
    Error: CPython 3.6 is not installed.
    cibuildwheel will not perform system-wide installs when running outside of CI.
    To build locally, install CPython 3.6 on this machine, or, disable this version of Python using CIBW_SKIP=cp36-macosx_*

    Download link: https://www.python.org/ftp/python/3.6.8/python-3.6.8-macosx10.9.pkg
    ```


# Configure a CI service

## GitHub Actions [linux/mac/windows] {: #github-actions}

To build Linux, Mac, and Windows wheels using GitHub Actions, create a `.github/workflows/build_wheels.yml` file in your repo.

!!! tab "Action"
    For GitHub Actions, `cibuildwheel` provides an action you can use. This is
    concise and enables easier auto updating via GitHub's Dependabot; see
    [Automatic updates](faq.md#automatic-updates).

    > .github/workflows/build_wheels.yml

    ```yaml
    {% include "../examples/github-minimal.yml" %}
    ```

    Use `env:` to pass [build options](options.md) and `with:` to set
    `package-dir: .`, `output-dir: wheelhouse` and `config-file: ''`
    locations (those values are the defaults).

!!! tab "pipx"
    The GitHub Actions runners have pipx installed, so you can easily build in
    just one line. This is internally how the action works; the main benefit of
    the action form is easy updates via GitHub's Dependabot.

    > .github/workflows/build_wheels.yml

    ```yaml
    name: Build

    on: [push, pull_request]

    jobs:
      build_wheels:
        name: Build wheels on ${{ matrix.os }}
        runs-on: ${{ matrix.os }}
        strategy:
          matrix:
            os: [ubuntu-20.04, windows-2019, macos-10.15]

        steps:
          - uses: actions/checkout@v3

          - name: Build wheels
            run: pipx run cibuildwheel==2.8.0

          - uses: actions/upload-artifact@v3
            with:
              path: ./wheelhouse/*.whl
    ```

!!! tab "Generic"
    This is the most generic form using setup-python and pip; it looks the most
    like the other CI examples. If you want to avoid having setup that takes
    advantage of GitHub Actions features or pipx being preinstalled, this might
    appeal to you.

    > .github/workflows/build_wheels.yml

    ```yaml
    name: Build

    on: [push, pull_request]

    jobs:
      build_wheels:
        name: Build wheels on ${{ matrix.os }}
        runs-on: ${{ matrix.os }}
        strategy:
          matrix:
            os: [ubuntu-20.04, windows-2019, macos-10.15]

        steps:
          - uses: actions/checkout@v3

          # Used to host cibuildwheel
          - uses: actions/setup-python@v3

          - name: Install cibuildwheel
            run: python -m pip install cibuildwheel==2.8.0

          - name: Build wheels
            run: python -m cibuildwheel --output-dir wheelhouse

          - uses: actions/upload-artifact@v3
            with:
              path: ./wheelhouse/*.whl
    ```


Commit this file, and push to GitHub - either to your default branch, or to a PR branch. The build should start automatically.

For more info on this file, check out the [docs](https://help.github.com/en/actions/reference/workflow-syntax-for-github-actions).

[`examples/github-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml) extends this minimal example with a demonstration of how to automatically upload the built wheels to PyPI.


## Azure Pipelines [linux/mac/windows] {: #azure-pipelines}

To build Linux, Mac, and Windows wheels on Azure Pipelines, create a `azure-pipelines.yml` file in your repo.

> azure-pipelines.yml

```yaml
{% include "../examples/azure-pipelines-minimal.yml" %}
```

Commit this file, enable building of your repo on Azure Pipelines, and push.

Wheels will be stored for you and available through the Pipelines interface. For more info on this file, check out the [docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema).

## Travis CI [linux/windows] {: #travis-ci}

To build Linux and Windows wheels on Travis CI, create a `.travis.yml` file in your repo.

> .travis.yml

```yaml
{% include "../examples/travis-ci-minimal.yml" %}
```

Commit this file, enable building of your repo on Travis CI, and push.

Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](deliver-to-pypi.md). For more info on `.travis.yml`, check out the [docs](https://docs.travis-ci.com/).

[`examples/travis-ci-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/travis-ci-deploy.yml) extends this minimal example with a demonstration of how to automatically upload the built wheels to PyPI.

## AppVeyor [linux/mac/windows] {: #appveyor}

To build Linux, Mac, and Windows wheels on AppVeyor, create an `appveyor.yml` file in your repo.

> appveyor.yml

```yaml
{% include "../examples/appveyor-minimal.yml" %}
```

Commit this file, enable building of your repo on AppVeyor, and push.

AppVeyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [AppVeyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](deliver-to-pypi.md) below.

For more info on this config file, check out the [docs](https://www.appveyor.com/docs/).

## CircleCI [linux/mac] {: #circleci}

To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

> .circleci/config.yml

```yaml
{% include "../examples/circleci-minimal.yml" %}
```

Commit this file, enable building of your repo on CircleCI, and push.

!!! note
    CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

CircleCI will store the built wheels for you - you can access them from the project console. Check out the CircleCI [docs](https://circleci.com/docs/2.0/configuration-reference/#section=configuration) for more info on this config file.

## Gitlab CI [linux] {: #gitlab-ci}

To build Linux wheels on Gitlab CI, create a `.gitlab-ci.yml` file in your repo,

> .gitlab-ci.yml

```yaml
{% include "../examples/gitlab-minimal.yml" %}
```

Commit this file, and push to Gitlab. The pipeline should start automatically.

Gitlab will store the built wheels for you - you can access them from the Pipelines view. Check out the Gitlab [docs](https://docs.gitlab.com/ee/ci/yaml/) for more info on this config file.

> ⚠️ Got an error? Check the [FAQ](faq.md).

# Next steps

Once you've got the wheel building successfully, you might want to set up [testing](options.md#test-command) or [automatic releases to PyPI](deliver-to-pypi.md#automatic-method).

<script>
  document.addEventListener('DOMContentLoaded', function() {
    $('a.toctree-l3, .rst-content h2').each(function(i, el) {
      var text = $(el).text()
      var match = text.match(/(.*) \[([a-z/]+)\]/);

      if (match) {
        var iconHTML = $.map(match[2].split('/'), function(ident) {
          switch (ident) {
            case 'linux':
              return '<i class="fa fa-linux" aria-hidden="true"></i>'
            case 'windows':
              return '<i class="fa fa-windows" aria-hidden="true"></i>'
            case 'mac':
              return '<i class="fa fa-apple" aria-hidden="true"></i>'
          }
        }).join(' ');

        $(el).append(
          $('<div>')
            .append(iconHTML)
            .css({float: 'right'})
        )
        $(el).contents()
          .filter(function(){ return this.nodeType == 3; }).first()
          .replaceWith(match[1]);
      }
    });
  });
</script>
