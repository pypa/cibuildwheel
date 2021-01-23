---
title: 'Setup'
---

# GitHub Actions [linux/mac/windows] {: #github-actions}

To build Linux, Mac, and Windows wheels using Github Actions, create a `.github/workflows/build.yml` file in your repo.

> build.yml
```yaml
{% include "../examples/github-minimal.yml" %}
```

Commit this file, and push to Github - either to your default branch, or to a PR branch. The build should start automatically.

For more info on this file, check out the [docs](https://help.github.com/en/actions/reference/workflow-syntax-for-github-actions).

[`examples/github-deploy.yml`](https://github.com/joerick/cibuildwheel/blob/master/examples/github-deploy.yml) extends this minimal example with a demonstration of how to automatically upload the built wheels to PyPI.

You can also use cibuildwheel directly as an action with `uses: joerick/cibuildwheel@v1.8.0`; this combines the download and run steps into a single action, and command line arguments are available via `with:`. This makes it easy to manage cibuildwheel updates via normal actions update mechanisms like dependabot, see [Automatic updates](faq.md#automatic-updates).

# Azure Pipelines [linux/mac/windows] {: #azure-pipelines}

To build Linux, Mac, and Windows wheels on Azure Pipelines, create a `azure-pipelines.yml` file in your repo.

> azure-pipelines.yml
```yaml
{% include "../examples/azure-pipelines-minimal.yml" %}
```

!!! note
    To support Python 3.5 on Windows, make sure to specify the use of `{vmImage: 'vs2017-win2016'}` on Windows, to ensure the required toolchain is available.

Commit this file, enable building of your repo on Azure Pipelines, and push.

Wheels will be stored for you and available through the Pipelines interface. For more info on this file, check out the [docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema).

# Travis CI [linux/mac/windows] {: #travis-ci}

To build Linux, Mac, and Windows wheels on Travis CI, create a `.travis.yml` file in your repo.

> .travis.yml
```yaml
{% include "../examples/travis-ci-minimal.yml" %}
```

Note that building Windows Python 2.7 wheels on Travis is unsupported unless using a newer compiler [via a workaround](cpp_standards.md).

Commit this file, enable building of your repo on Travis CI, and push.

Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](deliver-to-pypi.md). For more info on `.travis.yml`, check out the [docs](https://docs.travis-ci.com/).

[`examples/travis-ci-deploy.yml`](https://github.com/joerick/cibuildwheel/blob/master/examples/travis-ci-deploy.yml) extends this minimal example with a demonstration of how to automatically upload the built wheels to PyPI.

# CircleCI [linux/mac] {: #circleci}

To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

> .circleci/config.yml
```yaml
{% include "../examples/circleci-minimal.yml" %}
```

Commit this file, enable building of your repo on CircleCI, and push.

!!! note
    CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

CircleCI will store the built wheels for you - you can access them from the project console. Check out the CircleCI [docs](https://circleci.com/docs/2.0/configuration-reference/#section=configuration) for more info on this config file.

# Gitlab CI [linux] {: #gitlab-ci}

To build Linux wheels on Gitlab CI, create a `.gitlab-ci.yml` file in your repo,

> .gitlab-ci.yml
```yaml
{% include "../examples/gitlab-minimal.yml" %}
```

Commit this file, and push to Gitlab. The pipeline should start automatically.

Gitlab will store the built wheels for you - you can access them from the Pipelines view. Check out the Gitlab [docs](https://docs.gitlab.com/ee/ci/yaml/) for more info on this config file.

# AppVeyor [linux/mac/windows] {: #appveyor}

To build Linux, Mac, and Windows wheels on AppVeyor, create an `appveyor.yml` file in your repo.

> appveyor.yml

```yaml
{% include "../examples/appveyor-minimal.yml" %}
```

Commit this file, enable building of your repo on AppVeyor, and push.

AppVeyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [AppVeyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](deliver-to-pypi.md) below.

For more info on this config file, check out the [docs](https://www.appveyor.com/docs/).

> ⚠️ Got an error? Check the [FAQ](faq.md).

<script>
  document.addEventListener('DOMContentLoaded', function() {
    $('.toctree-l2 a, .rst-content h1').each(function(i, el) {
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
