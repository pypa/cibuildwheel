---
title: 'Setup'
---

# Setup

## Run cibuildwheel locally (optional) {: #local}

Before getting to CI setup, it can be convenient to test cibuildwheel
locally to quickly iterate and track down issues without even touching CI.

Install cibuildwheel and run a build like this:

```sh
# using pipx (https://github.com/pypa/pipx)
pipx run cibuildwheel

# or,
pip install cibuildwheel
cibuildwheel
```

You should see the builds taking place. You can experiment with options using environment variables or pyproject.toml.

!!! tab "Environment variables"

    cibuildwheel will read config from the environment. Syntax varies, depending on your shell:

    > POSIX shell (Linux/macOS)

    ```sh
    # run a command to set up the build system
    export CIBW_BEFORE_ALL='uname -a'

    cibuildwheel
    ```

    > CMD (Windows)

    ```bat
    set CIBW_BEFORE_ALL='uname -a'

    cibuildwheel
    ```

!!! tab "pyproject.toml"

    If you write your options into [`pyproject.toml`](options.md#configuration-file), you can work on your options locally, and they'll be automatically picked up when running in CI.

    > pyproject.toml

    ```
    [tool.cibuildwheel]
    before-all = "uname -a"
    ```

    Then invoke cibuildwheel, like:

    ```console
    cibuildwheel
    ```

### Linux builds

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

### macOS / Windows builds {: #macos-windows}

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

### iOS builds

Pre-requisite: You must be building on a macOS machine, with Xcode installed.
The Xcode installation must have an iOS SDK available. To check if an iOS SDK
is available, open the Xcode settings panel, and check the Platforms tab.

To build iOS wheels, pass in `--platform ios` when invoking `cibuildwheel`. This will
build three wheels:

* An ARM64 wheel for iOS devices;
* An ARM64 wheel for the iOS simulator; and
* An x86_64 wheel for the iOS simulator.

Alternatively, you can build only wheels for iOS devices by using
`--platform iphoneos`; or only wheels for iOS simulators by using
`--platform iphonesimulator`.

Building iOS wheel also requires a working macOS Python configuration. See the notes
on [macOS builds](setup.md#macos-windows) for details about configuration.

iOS builds will honor the `IPHONEOS_DEPLOYMENT_TARGET` environment variable to set the
minimum supported API version for generated wheels. This will default to `13.0` if the
environment variable isn't set.

If tests have been configured, the test suite will be executed on the simulator
matching the architecture of the build machine - that is, if you're building on
an ARM64 macOS machine, the ARM64 wheel will be tested on an ARM64 simulator.

### Pyodide (WebAssembly) builds (experimental)

Pre-requisite: you need to have a matching host version of Python (unlike all
other cibuildwheel platforms). Linux host highly recommended; macOS hosts may
work (e.g. invoking `pytest` directly in [`CIBW_TEST_COMMAND`](options.md#test-command) is [currently failing](https://github.com/pyodide/pyodide/issues/4802)) and Windows hosts will not work.

You must target pyodide with `--platform pyodide` (or use `--only` on the identifier).

## Configure a CI service

### GitHub Actions [linux/mac/windows] {: #github-actions}

To build Linux, macOS, and Windows wheels using GitHub Actions, create a `.github/workflows/build_wheels.yml` file in your repo.

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
    {% include "../examples/github-pipx.yml" %}
    ```

!!! tab "Generic"
    This is the most generic form using setup-python and pip; it looks the most
    like the other CI examples. If you want to avoid having setup that takes
    advantage of GitHub Actions features or pipx being preinstalled, this might
    appeal to you.

    > .github/workflows/build_wheels.yml
    {%
       include-markdown "../README.md"
       start="<!--generic-github-start-->"
       end="<!--generic-github-end-->"
    %}

Commit this file, and push to GitHub - either to your default branch, or to a PR branch. The build should start automatically.

For more info on this file, check out the [docs](https://help.github.com/en/actions/reference/workflow-syntax-for-github-actions).

[`examples/github-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml) extends this minimal example to include iOS and Pyodide builds, and a demonstration of how to automatically upload the built wheels to PyPI.


### Azure Pipelines [linux/mac/windows] {: #azure-pipelines}

To build Linux, Mac, and Windows wheels on Azure Pipelines, create a `azure-pipelines.yml` file in your repo.

> azure-pipelines.yml

```yaml
{% include "../examples/azure-pipelines-minimal.yml" %}
```

Commit this file, enable building of your repo on Azure Pipelines, and push.

Wheels will be stored for you and available through the Pipelines interface. For more info on this file, check out the [docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema).

### Travis CI [linux/windows] {: #travis-ci}

To build Linux and Windows wheels on Travis CI, create a `.travis.yml` file in your repo.

> .travis.yml

```yaml
{% include "../examples/travis-ci-minimal.yml" %}
```

Commit this file, enable building of your repo on Travis CI, and push.

Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](deliver-to-pypi.md). For more info on `.travis.yml`, check out the [docs](https://docs.travis-ci.com/).

[`examples/travis-ci-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/travis-ci-deploy.yml) extends this minimal example with a demonstration of how to automatically upload the built wheels to PyPI.

### AppVeyor [linux/mac/windows] {: #appveyor}

To build Linux, Mac, and Windows wheels on AppVeyor, create an `appveyor.yml` file in your repo.

> appveyor.yml

```yaml
{% include "../examples/appveyor-minimal.yml" %}
```

Commit this file, enable building of your repo on AppVeyor, and push.

AppVeyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [AppVeyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](deliver-to-pypi.md) below.

For more info on this config file, check out the [docs](https://www.appveyor.com/docs/).

### CircleCI [linux/mac] {: #circleci}

To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

> .circleci/config.yml

```yaml
{% include "../examples/circleci-minimal.yml" %}
```

Commit this file, enable building of your repo on CircleCI, and push.

!!! note
    CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

CircleCI will store the built wheels for you - you can access them from the project console. Check out the CircleCI [docs](https://circleci.com/docs/2.0/configuration-reference/#section=configuration) for more info on this config file.

### Gitlab CI [linux] {: #gitlab-ci}

To build Linux wheels on Gitlab CI, create a `.gitlab-ci.yml` file in your repo,

> .gitlab-ci.yml

```yaml
{% include "../examples/gitlab-minimal.yml" %}
```

Commit this file, and push to Gitlab. The pipeline should start automatically.

Gitlab will store the built wheels for you - you can access them from the Pipelines view. Check out the Gitlab [docs](https://docs.gitlab.com/ee/ci/yaml/) for more info on this config file.

### Cirrus CI [linux/mac/windows] {: #cirrus-ci}

To build Linux, Mac, and Windows wheels on Cirrus CI, create a `.cirrus.yml` file in your repo,

> .cirrus.yml

```yaml
{% include "../examples/cirrus-ci-minimal.yml" %}
```

Commit this file, enable building of your repo on Cirrus CI, and push.

Cirrus CI will store the built wheels for you - you can access them from the individual task view. Check out the Cirrus CI [docs](https://cirrus-ci.org/guide/writing-tasks/) for more info on this config file.

> ⚠️ Got an error? Check the [FAQ](faq.md).

## Next steps

Once you've got the wheel building successfully, you might want to set up [testing](options.md#test-command) or [automatic releases to PyPI](deliver-to-pypi.md#automatic-method).

<script>
  document.addEventListener('DOMContentLoaded', function() {
    $('.toctree-l3>a, .rst-content h3').each(function(i, el) {
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
