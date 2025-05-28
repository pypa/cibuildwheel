---
title: Delivering to PyPI
---

# Delivering to PyPI

After you've built your wheels, you'll probably want to deliver them to PyPI.

## Automatic method

If you don't need much control over the release of a package, you can set up
your CI provider to deliver the wheels straight to PyPI. You just need to bump the
version and tag it.

The exact way to set it up varies, depending on which CI provider you're using. But generally, the process goes like this:

- Build your wheels with cibuildwheel
- Build an sdist with the [build](https://github.com/pypa/build) tool
- Check that the current CI run is happening during a release (e.g. it's in response to a vXX tag)
- Collect these assets together onto one runner
- Upload them to PyPI using `twine upload <paths>`

### GitHub Actions

GitHub actions has pipx in all the runners as a supported package manager, as well as `pypa/gh-action-pypi-publish`, which can be used instead of twine. Alongside your existing job(s) that runs cibuildwheel to make wheels, you will probably want to build an sdist:

```yaml
  make_sdist:
    name: Make SDist
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Optional, use if you use setuptools_scm
        submodules: true  # Optional, use if you have submodules

    - name: Build SDist
      run: pipx run build --sdist

    - uses: actions/upload-artifact@v4
      with:
        name: cibw-sdist
        path: dist/*.tar.gz
```

Then, you need to publish the artifacts that the previous jobs have built. This final job should run only on release or tag, depending on your preference. It gathers the artifacts from the sdist and wheel jobs and uploads them to PyPI. The release environment (`pypi` in the example below) will be created the first time this workflow runs.

```yaml
  upload_all:
    needs: [build_wheels, make_sdist]
    environment: pypi
    permissions:
      id-token: write
    runs-on: ubuntu-latest
    if: github.event_name == 'release' && github.event.action == 'published'
    steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: cibw-*
        path: dist
        merge-multiple: true

    - uses: pypa/gh-action-pypi-publish@release/v1
```

The above example uses PyPI Trusted Publishing to deliver the wheels, which requires some configuration on the PyPI side for a [new project](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc) or an [existing project](https://docs.pypi.org/trusted-publishers/adding-a-publisher). You can use Dependabot to keep the publish action up to date.

See
[`examples/github-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml)
for an example configuration that automatically uploads wheels to PyPI. Also see
[scikit-hep.org/developer/gha_wheels](https://scikit-hep.org/developer/gha_wheels)
for a complete guide.

### TravisCI

See
[`examples/travis-ci-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/travis-ci-deploy.yml)
for an example configuration.

## Manual method

On your development machine, install [pipx](https://pipx.pypa.io/) and do the following:

```bash
# Either download the SDist from your CI, or make it:
# Clear out your 'dist' folder.
rm -rf dist
# Make a source distribution
pipx run build --sdist

# 🏃🏻
# Go and download your wheel files from wherever you put them. e.g. your CI
# provider can be configured to store them for you. Put them all into the
# 'dist' folder.

# Upload using 'twine'
pipx run twine upload dist/*
```
