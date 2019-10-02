## Azure Pipelines [linux/mac/windows]

Using Azure pipelines, you can build all three platforms on the same service. Create a `azure-pipelines.yml` file in your repo.

**azure-pipelines.yml**
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
    - {task: UsePythonVersion@0, inputs: {versionSpec: '2.7', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '2.7', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.5', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.5', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.6', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.6', architecture: x64}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.7', architecture: x86}}
    - {task: UsePythonVersion@0, inputs: {versionSpec: '3.7', architecture: x64}}
    - script: choco install vcpython27 -f -y
      displayName: Install Visual C++ for Python 2.7
    - bash: |
        python -m pip install --upgrade pip
        pip install cibuildwheel==0.12.0
        cibuildwheel --output-dir wheelhouse .
    - task: PublishBuildArtifacts@1
      inputs: {pathtoPublish: 'wheelhouse'}
```

## Travis CI [linux/mac]

To build Linux and Mac wheels on Travis CI, create a `.travis.yml` file in your repo.

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

Then setup a deployment method by following the [Travis CI deployment docs](https://docs.travis-ci.com/user/deployment/), or see [Delivering to PyPI](#delivering-to-pypi) below.

## CircleCI [linux/mac]
    
To build Linux and Mac wheels on CircleCI, create a `.circleci/config.yml` file in your repo,

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
            pip install --user cibuildwheel
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
            pip install --user cibuildwheel
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

!!! note
    CircleCI doesn't enable free macOS containers for open source by default, but you can ask for access. See [here](https://circleci.com/docs/2.0/oss/#overview) for more information.

CircleCI will store the built wheels for you - you can access them from the project console.

## AppVeyor [windows]

To build Windows wheels on AppVeyor, create an `appveyor.yml` file in your repo.

```yaml
build_script:
  - pip install cibuildwheel==0.12.0
  - cibuildwheel --output-dir wheelhouse
artifacts:
  - path: "wheelhouse\\*.whl"
    name: Wheels
```
    
AppVeyor will store the built wheels for you - you can access them from the project console. Alternatively, you may want to store them in the same place as the Travis CI build. See [AppVeyor deployment docs](https://www.appveyor.com/docs/deployment/) for more info, or see [Delivering to PyPI](#delivering-to-pypi) below.

Commit those files, enable building of your repo on Travis CI and AppVeyor, and push.

All being well, you should get wheels delivered to you in a few minutes. 

> ⚠️ Got an error? Check the [checklist](#it-didnt-work) below.
