---
title: 'Setup'
---

# Build your wheel locally

Before starting to configure cibuildwheel, it's useful to try to build a wheel
on your local machine. It's much easier to debug problems on your machine than
inside a CI system!

## Invoking a build

Start with a clean checkout of your project, inside a new clean virtual
environment. Make sure your `pip` is up to date, and then invoke:

```shell
pip wheel -w wheelhouse .
```

If your build completes without a problem, congratulations! You can move on to
the next step. Otherwise, you might have one of the following issues:

### Missing build dependencies

If your build needs Python dependencies, you can resolve this by adding
package names to the
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

If you have other dependencies, you should make a note of these, you'll be
able to install them using the cibuildwheel options [`CIBW_BEFORE_BUILD`](options.md#before-build) or
[`CIBW_BEFORE_ALL`](options.md#before-all).

### Actions you need to perform before building

You might need to run some other commands before building, like running a
script that performs codegen or downloading some data that's not stored in
your source tree. There are a couple ways to deal with this:

-   Incorporate this into your build process, by adding it to your package's
    `setup.py`. You can add extra build steps using a structure like this:

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

    This method is usually preferred because in addition to adding being
    included in the wheel build process, it will help users building from
    source tarballs as well.

-   Alternatively, you can instruct cibuildwheel to run commands before
    building your wheel. Take a look at the cibuildwheel options
    [`CIBW_BEFORE_BUILD`](options.md#before-build) or
    [`CIBW_BEFORE_ALL`](options.md#before-all).

### Environment variables

Your wheel build might need some environment variables to be set. Consider
incorporating these into setup.py to allow source tarballs to build (for
example, using [`extra_compile_args` or
`extra_link_args`](https://docs.python.org/3/distutils/setupscript.html#other-options)),
but otherwise, make a note of these for inclusion in the cibuildwheel option
[`CIBW_ENVIRONMENT`](options.md#environment).

# Run cibuildwheel locally

`cibuildwheel --platform linux`

TODO

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


    You can use `env:` with the action just like you would with `run:`; you can
    also use `with:` to set the command line options: `package-dir: .` and
    `output-dir: wheelhouse` (those values are the defaults).

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
          - uses: actions/checkout@v2

          - name: Build wheels
            run: pipx run cibuildwheel==2.0.0a3

          - uses: actions/upload-artifact@v2
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
          - uses: actions/checkout@v2

          # Used to host cibuildwheel
          - uses: actions/setup-python@v2

          - name: Install cibuildwheel
            run: python -m pip install cibuildwheel==2.0.0a3

          - name: Build wheels
            run: python -m cibuildwheel --output-dir wheelhouse

          - uses: actions/upload-artifact@v2
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

# Further setup

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
