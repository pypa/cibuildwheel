## Azure Pipelines [linux/mac/windows]

Using Azure pipelines, you can build all three platforms on the same service. Create a `azure-pipelines.yml` file in your repo.

> azure-pipelines.yml
```yaml
jobs:
- job: linux
  pool: {vmImage: 'Ubuntu-16.04'}
  steps: 
    - task: UsePythonVersion@0
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.12.0
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
- job: macos
  pool: {vmImage: 'macOS-10.13'}
  steps: 
    - task: UsePythonVersion@0
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.12.0
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
- job: windows
  pool: {vmImage: 'vs2017-win2016'}
  steps: 
    - task: UsePythonVersion@0
    - script: choco install vcpython27 -f -y
      displayName: Install Visual C++ for Python 2.7
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.12.0
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
```

Commit this file, enable building of your repo on Azure Pipelines, and push.

Wheels will be stored for you and available through the Pipelines interface. For more info on this file, check out the [docs](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema).

## Travis CI [linux/mac]

To build Linux and Mac wheels on Travis CI, create a `.travis.yml` file in your repo.

> .travis.yml
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

script:
  - $PIP install cibuildwheel==0.12.0
  - cibuildwheel --output-dir wheelhouse
```

To build on Windows too, add this matrix entry:
```yaml
    - os: windows
      language: shell
      before_install:
        - choco install python3 --version 3.6.8 --no-progress -y
      env:
        - PATH=/c/Python36:/c/Python36/Scripts:$PATH
```

Note that building Windows Python 2.7 wheels on Travis is unsupported.

Commit this file, enable building of your repo on Travis CI, and push.

Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](deliver-to-pypi.md). For more info on `.travis.yml`, check out the [docs](https://docs.travis-ci.com/).

## CircleCI [linux/mac]

To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

> .circleci/config.yml
```yaml
version: 2

jobs:
  linux-wheels:
    working_directory: ~/linux-wheels
    docker:
      - image: circleci/python:3.6
    steps:
      - checkout
      - setup_remote_docker
      - run:
          name: Build the Linux wheels.
          command: |
            pip install --user cibuildwheel==0.12.0
            cibuildwheel --output-dir wheelhouse
      - store_artifacts:
          path: wheelhouse/
  
  osx-wheels:
    working_directory: ~/osx-wheels
    macos:
      xcode: "10.0.0"
    steps:
      - checkout
      - run:
          name: Build the OS X wheels.
          command: |
            pip install --user cibuildwheel==0.12.0
            cibuildwheel --output-dir wheelhouse
      - store_artifacts:
          path: wheelhouse/

workflows:
  version: 2
  all-tests:
    jobs:
      - linux-wheels
      - osx-wheels
```

Commit this file, enable building of your repo on CircleCI, and push.

!!! note
    CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

CircleCI will store the built wheels for you - you can access them from the project console. Check out the CircleCI [docs](https://circleci.com/docs/2.0/configuration-reference/#section=configuration) for more info on this config file.

## AppVeyor [windows]

To build Windows wheels on AppVeyor, create an `appveyor.yml` file in your repo.

> appveyor.yml

```yaml
build_script:
  - pip install cibuildwheel==0.12.0
  - cibuildwheel --output-dir wheelhouse
artifacts:
  - path: "wheelhouse\\*.whl"
    name: Wheels
```

Commit this file, enable building of your repo on AppVeyor, and push.

AppVeyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [AppVeyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](deliver-to-pypi.md) below.

For more info on this config file, check out the [docs](https://www.appveyor.com/docs/).

> ⚠️ Got an error? Check the [FAQ](faq.md).

<script> 
  document.addEventListener('DOMContentLoaded', function() {
    $('.toctree-l2 a, .rst-content h2').each(function(i, el) {
      var text = $(el).text()
      var match = text.match(/(.*) \[([a-z/]+)\]/);

      if (match) {
        var iconHTML = match[2].split('/').map(function(ident) {
          switch (ident) {
            case 'linux':
              return '<i class="fa fa-linux" aria-hidden="true"></i>'
            case 'windows':
              return '<i class="fa fa-windows" aria-hidden="true"></i>'
            case 'mac':
              return '<i class="fa fa-apple" aria-hidden="true"></i>'
          }
        }).join(' ');
        $(el).html(match[1] + ' ' + iconHTML)
      }
    });
  });
</script>