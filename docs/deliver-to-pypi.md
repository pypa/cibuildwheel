---
title: Delivering to PyPI
---

After you've built your wheels, you'll probably want to deliver them to PyPI.

### Manual method

On your development machine, do the following...

```bash
# Clear out your 'dist' folder.
rm -rf dist
# Make a source distribution
python setup.py sdist

# 🏃🏻
# Go and download your wheel files from wherever you put them. e.g. your CI
# provider can be configured to store them for you. Put them all into the
# 'dist' folder.

# Upload using 'twine' (you may need to 'pip install twine')
twine upload dist/*
```

### Semi-automatic method using wheelhouse-uploader

Obviously, manual steps are for chumps, so we can automate this a little by using [wheelhouse-uploader](https://github.com/ogrisel/wheelhouse-uploader).

> Quick note from me - using S3 as a storage didn't work due to a [bug](https://issues.apache.org/jira/browse/LIBCLOUD-792) in libcloud. Feel free to use my fork of that package that fixes the bug `pip install https://github.com/joerick/libcloud/archive/v1.5.0-s3fix.zip`

### Automatic method

If you don't need much control over the release of a package, you can set up cibuildwheel to deliver the wheels straight to PyPI. This doesn't require anycloud storage to work - you just need to bump the version and tag it.

[`examples/travis-ci-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/travis-ci-deploy.yml) and [`examples/github-deploy.yml`](https://github.com/pypa/cibuildwheel/blob/main/examples/github-deploy.yml) are example configurations that automatically upload wheels to PyPI. Also check out [this example repo](https://github.com/pypa/cibuildwheel-autopypi-example) for more detailed instructions on how to set this up.
