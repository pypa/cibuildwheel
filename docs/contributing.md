---
title: Contributing
---

Wheel-building can be pretty complex. I expect users to find many edge-cases - please help the rest of the community out by documenting these, adding features to support them, and reporting bugs.

I plan to be pretty liberal in accepting pull requests, as long as they align with the design goals below.

`cibuildwheel` is indie open source. We're not paid to work on this.

Design Goals
------------

- `cibuildwheel` should wrap the complexity of wheel building.
- The user interface to `cibuildwheel` is the build script (e.g. `.travis.yml`). Feature additions should not increase the complexity of this script.
- Options should be environment variables (these lend themselves better to YML config files). They should be prefixed with `CIBW_`.
- Options should be generalise to all platforms. If platform-specific options are required, they should be namespaced e.g. `CIBW_TEST_COMMAND_MACOS`

Other notes:

- The platforms are very similar, until they're not. I'd rather have straight-forward code than totally DRY code, so let's keep airy platfrom abstractions to a minimum.
- I might want to break the options into a shared config file one day, so that config is more easily shared. That has motivated some of the design decisions.

### cibuildwheel's relationship with build errors

cibuildwheel doesn't really do anything itself - it's always deferring to other tools (pip, wheel, auditwheel, delocate, docker). Without cibuildwheel, the process is really fragmented. Different tools, across different OSs need to be stitched together in just the right way to make it work.

We're not responsible for errors in those tools, for fixing errors/crashes there. But cibuildwheel's job is providing users with an 'integrated' user experience across those tools. We provide an abstraction. The user says 'build me some wheels', not 'open the docker container, build a wheel with pip, fix up the symbols with auditwheel' etc.  However, errors have a habit of breaking abstractions. And this is where users get confused, because the mechanism of cibuildwheel is laid bare, and they must understand a little bit how it works to debug.

So, if we can, I'd like to improve the experience on errors as well. In [this](https://github.com/joerick/cibuildwheel/issues/139) case, it takes a bit of knowledge to understand that the linux builds are happening in a totally different OS via docker, that the linked symbols won't match, that auditwheel will fail because of this. A problem with how the tools fit together, instead of the tools themselves.

Maintainer notes
----------------

## Local testing

You should run:

```python
python3 -m venv venv
. venv/bin/activate
pip install -e .[dev]
```

To prepare a development environment.

## Testing minimal configs


cibuildwheel's _minimal_ example configs can be tested on a simple project on cibuildwheel's existing CI. These should be run whenever the minimal configs change.

To test minimal configs, make sure you have a clean git repo, then run the script:

```bash
bin/run_example_ci_configs.py
```

The script will create an isolated 'orphan' commit containing all the minimal config CI files, and a simple C extension project, and push that to a branch on the `origin` repo. The project's CI is already set up to run on branch push, so will begin testing.

The script then outputs a Markdown table that can be copy/pasted into a PR to monitor and record the test.

## Preparing environments

This has been moved to using docker, so you only need the following instructions if you add `--no-docker` to avoid using docker.

The dependency update script in the next section requires multiple python versions installed. One way to do this is to use `pyenv`:

```bash
pyenv install 2.7.18
pyenv install 3.5.9
pyenv install 3.6.11
pyenv install 3.7.8
# Optionally add 3.8 and make it the local version;
# otherwise assuming 3.8+ already is your current python version
```

Then, you need to make the required virtual environments:

```bash
$(pyenv prefix 2.7.18)/bin/python -m pip install virtualenv
$(pyenv prefix 2.7.18)/bin/python -m virtualenv env27
$(pyenv prefix 3.5.9)/bin/python -m venv env35
$(pyenv prefix 3.6.11)/bin/python -m venv env36
$(pyenv prefix 3.7.8)/bin/python -m venv env37
```

<!-- Note for fish users: use zsh/bash for these lines for now, there's not a nice one-line fish replacement -->

And, you need to install the requirements into each environment:

```bash
for f in env*/bin/pip; do $f install pip-tools; done
```


## Making a release

Before making a release, ensure pinned dependencies are up-to-date. Run the script:

```bash
bin/make_dependency_update_pr.py
```

If updates are needed, this will push a PR with those updates for the CI to test. Once green, merge this PR.

Then, increment the project version number using:

```bash
bin/bump_version.py
```

You'll be prompted to enter the new version number. Update the changelog when prompted. The script will create a 'bump version' commit and version tag.

Finally, cut the release and upload to PyPI/Github.

```bash
rm -rf dist
python setup.py sdist bdist_wheel
twine upload dist/*
git push && git push --tags
```
