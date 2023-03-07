This is a summary of the Python versions and platforms covered by the different CI platforms:

|         | 3.7       | 3.8                                   | 3.9       | 3.10      | 3.11           |
|---------|-----------|---------------------------------------|-----------|-----------|----------------|
| Linux   | Travis CI | AppVeyor¹ / Azure Pipelines / GitLab¹ | CircleCI¹ | Cirrus CI | GitHub Actions |
| macOS   | Travis CI | AppVeyor¹ / Azure Pipelines           | CircleCI¹ | Cirrus CI | GitHub Actions |
| Windows | Travis CI | AppVeyor¹ / Azure Pipelines / GitLab¹ |           | Cirrus CI | GitHub Actions |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.7.
