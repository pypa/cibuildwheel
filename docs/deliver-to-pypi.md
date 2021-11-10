---
title: Delivering to PyPI
---

After you've built your wheels, you'll probably want to deliver them to PyPI.

## Manual method

On your development machine, install [pipx](https://pypa.github.io/pipx/) and do the following:

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

# Upload using 'twine' (you may need to 'pip install twine')
pipx run twine upload dist/*
```

## Automatic method

If you don't need much control over the release of a package, you can set up
cibuildwheel to deliver the wheels straight to PyPI. You just need to bump the
version and tag it.

### Generic instructions

You'll want to build your SDist with [build](https://github.com/pypa/build) and your wheels with cibuildwheel. If you can make the files available as
downloadable artifacts, this make testing before releases easier (depending on your CI provider's options). The "publish" job/step should collect the
files, and then run `twine upload <paths>` (possibly via [pipx](https://github.com/pypa/pipx)); this should only happen on tags or "releases".

### GitHub Actions

GitHub actions has pipx in all the runners as a supported package manager, as
well as several useful actions. You will probably want to build an SDist:

```yaml
  make_sdist:
    name: Make SDist
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
      with:
        fetch-depth: 0  # Optional, use if you use setuptools_scm
        submodules: true  # Optional, use if you have submodules

    - name: Build SDist
      run: pipx run build --sdist

    - uses: actions/upload-artifact@v2
      with:
        path: dist/*.tar.gz
```

You'll want to download the artifacts in a final job that only runs on release
or tag (depending on your preference):

```yaml
  upload_all:
    needs: [build_wheels, make_sdist]
    runs-on: ubuntu-latest
    if: github.event_name == 'release' && github.event.action == 'published'
    steps:
    - uses: actions/download-artifact@v2
      with:
        name: artifact
        path: dist

    - uses: pypa/gh-action-pypi-publish@v1.4.2
      with:
        user: __token__
        password: ${{ secrets.pypi_password }}
```

You should use dependabot to keep the publish action up to date. In the above
example, the same name (the default, "artifact" is used for all upload-artifact
runs, so we can just download all of the in one step into a common directory.

See
[`examples/github-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml)
for an example configuration that automatically upload wheels to PyPI. Also see
[scikit-hep.org/developer/gha_wheels](https://scikit-hep.org/developer/gha_wheels)
for a complete guide.

### TravisCI

See
[`examples/travis-ci-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/travis-ci-deploy.yml)
for an example configuration.
