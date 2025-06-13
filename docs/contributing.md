---
title: Contributing
---

# Contributing

Wheel-building can be pretty complex. We expect users to find edge-cases - please help the rest of the community out by documenting these, adding features to support them, and reporting bugs.

If you have an idea for a modification or feature, it's probably best to raise an issue first and discuss it with the maintainer team. Once we have rough consensus on a design, begin work in a PR.

`cibuildwheel` is indie open source. We're not paid to work on this.

Everyone contributing to the cibuildwheel project is expected to follow the [PSF Code of Conduct](https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md).

## Design Goals

- `cibuildwheel` should wrap the complexity of wheel building.
- The user interface to `cibuildwheel` is the build script (e.g. `.travis.yml`). Feature additions should not increase the complexity of this script.
- Options should be environment variables (these lend themselves better to YAML config files). They should be prefixed with `CIBW_`.
- Options should be generalised to all platforms. If platform-specific options are required, they should be namespaced e.g. `CIBW_TEST_COMMAND_MACOS`

Other notes:

- The platforms are very similar, until they're not. I'd rather have straightforward code than totally DRY code, so let's keep airy platform abstractions to a minimum.
- I might want to break the options into a shared config file one day, so that config is more easily shared. That has motivated some of the design decisions.

### cibuildwheel's relationship with build errors

cibuildwheel doesn't really do anything itself - it's always deferring to other tools (pip, wheel, auditwheel, delocate, docker). Without cibuildwheel, the process is really fragmented. Different tools, across different OSs need to be stitched together in just the right way to make it work.

We're not responsible for errors in those tools, for fixing errors/crashes there. But cibuildwheel's job is providing users with an 'integrated' user experience across those tools. We provide an abstraction. The user says 'build me some wheels', not 'open the docker container, build a wheel with pip, fix up the symbols with auditwheel' etc.  However, errors have a habit of breaking abstractions. And this is where users get confused, because the mechanism of cibuildwheel is laid bare, and they must understand a little bit how it works to debug.

So, if we can, I'd like to improve the experience on errors as well. In [this](https://github.com/pypa/cibuildwheel/issues/139) case, it takes a bit of knowledge to understand that the Linux builds are happening in a different OS via Docker, that the linked symbols won't match, that auditwheel will fail because of this. A problem with how the tools fit together, instead of the tools themselves.

## Development

### Running the tests

When making a change to the codebase, you can run tests locally for quicker feedback than the CI runs on a PR. You can run them directly, but the easiest way to run tests is using [nox](https://nox.thea.codes/).

You can run all the tests locally by doing:

```bash
nox -s tests
```

However, because this takes a while, you might prefer to be more specific.

#### Unit tests

To run the project's unit tests, do:

```bash
nox -s tests -- unit_test
```

There are a few custom options to enable different parts of the test suite - check `nox -s tests -- unit_test --help` for details.

If you're calling this a lot, you might consider using the `-r` or `-R` arguments to nox to make it a bit faster. This calls pytest under the hood, so to target a specific test, use pytest's `-k` option after the `--` above to select a specific test.

#### Integration tests

To run the project's integration tests, do:

```bash
nox -s tests -- test
```

The integration test suite is big - it can take more than 30 minutes to run the whole thing.

Because it takes such a long time, normally you'd choose specific tests to run locally, and rely on the project's CI for the rest. Use pytest's `-k` option to choose specific tests. You can pass a test name or a filename, it'll run everything that matches.

```bash
nox -s tests -- test -k <test_name_or_filename>
# e.g.
nox -s tests -- test -k before_build
```

A few notes-

- Because they run inside a container, Linux tests can run on all platforms where Docker is installed, so they're convenient for running integration tests locally. Set the `--platform` flag on pytest to do this: `nox -s tests -- test --platform linux`.

- Running the macOS integration tests requires _system installs_ of Python from python.org for all the versions that are tested. We won't attempt to install these when running locally, but you can do so manually using the URL in the error message that is printed when the install is not found.

- The ['enable groups'](options.md#enable) run by default are just 'cpython-prerelease' and 'cpython-freethreading'. You can add other groups like pypy or graalpy by passing the `--enable` argument to pytest, i.e. `nox -s tests -- test --enable pypy`. On GitHub PRs, you can add a label to the PR to enable these groups.

#### Running pytest directly

More advanced users might prefer to invoke pytest directly. Set up a [dev environment](#setting-up-a-dev-environment), then,

```bash
# run the unit tests
pytest unit_test
# run the whole integration test suite
pytest test
# run a specific integration test
pytest test -k test_build_frontend_args
# run a specific integration test on a different platform
CIBW_PLATFORM=linux pytest test -k test_build_frontend_args
```

### Linting, docs

Most developer tasks have a nox interface. This allows you to very simply run tasks without worrying about setting up a development environment (as shown below). This is slower than setting up a development environment and reusing it, but has the (important) benefit of being highly reproducible; an earlier run does not affect a current run, or anything else on your machine.

You can see a list of sessions by typing `nox -l`; here are a few common ones:

```console
nox -s lint                    # Run the linters (default)
nox -s tests [-- PYTEST-ARGS]  # Run the tests   (default)
nox -s docs                    # Build and serve the documentation
nox -s build                   # Make SDist and wheel
```

More advanced users can run the update scripts:

```console
nox -s update_constraints # update all constraints files in cibuildwheel/resources
nox -s update_pins        # update tools, python interpreters & docker images used by cibuildwheel
```

### Setting up a dev environment

A dev environment isn't required for any of the `nox` tasks above. However, a dev environment is still useful, to be able to point an editor at, and a few other jobs.

cibuildwheel uses dependency groups. Set up a dev environment with UV by doing

```bash
uv sync
```

Or, if you're not using `uv`, you can do:

```bash
python3 -m venv .venv
source .venv/bin/activate
pipx run dependency-groups dev | xargs pip install -e.
```

Your virtualenv is at `.venv`.

## Maintainer notes

### Testing sample configs

cibuildwheel's  example configs can be tested on a simple project on cibuildwheel's existing CI. These should be run whenever the minimal configs change.

To test minimal configs, make sure you have a clean git repo, then run the script:

```bash
bin/run_example_ci_configs.py
```

The script will create an isolated 'orphan' commit containing all the minimal config CI files, and a simple C extension project, and push that to a branch on the `origin` repo. The project's CI is already set up to run on branch push, so will begin testing.

You can test any other configs using `bin/run_example_ci_configs.py CONFIG_PATH`, e.g.

```bash
bin/run_example_ci_configs.py examples/github-with-qemu.yml
```

The script then outputs a Markdown table that can be copy/pasted into a PR to monitor and record the test.

### Preparing environments

This has been moved to using docker, so you only need the following instructions if you add `--no-docker` to avoid using docker.

The dependency update script in the next section requires multiple python versions installed. One way to do this is to use `pyenv`:

```bash
pyenv install 3.7.8
# Optionally add 3.8 and make it the local version;
# otherwise assuming 3.8+ already is your current python version
```

Then, you need to make the required virtual environments:

```bash
$(pyenv prefix 3.7.8)/bin/python -m venv env37
```

<!-- Note for fish users: use zsh/bash for these lines for now, there's not a nice one-line fish replacement -->

And, you need to install the requirements into each environment:

```bash
for f in env*/bin/pip; do $f install pip-tools; done
```

### Making a release

Before making a release, ensure pinned dependencies are up-to-date. Autoupdates are run weekly, with a PR being raised with any changes as required, so just make sure the latest one is merged before continuing.

Then, increment the project version number using:

```bash
bin/bump_version.py
```

(or `nox -s bump_version`) You'll be prompted to enter the new version number. Update the changelog when prompted. The script will create a 'bump version' commit and version tag.

Finally, cut the release and push to GitHub.

```bash
git push && git push --tags
```

Then head to https://github.com/pypa/cibuildwheel/releases and create a GitHub release from the new tag, pasting in the changelog entry. Once the release is created inside GitHub, a CI job will create the assets and upload them to PyPI.

If there were any schema updates, run `pipx run ./bin/generate_schema.py --schemastore > partial-cibuildwheel.json` and contribute the changes to SchemaStore.
