This is a summary of the Python versions and platforms covered by the different CI platforms:

|         | 3.8                                                    | 3.9                   | 3.10      | 3.11           |
|---------|--------------------------------------------------------|-----------------------|-----------|----------------|
| Linux   | AppVeyor¹ / Azure Pipelines / GitLab¹ / GitHub Actions | CircleCI¹ / Travis CI | Cirrus CI | GitHub Actions |
| macOS   | AppVeyor¹ / Azure Pipelines                            | CircleCI¹ / Travis CI | Cirrus CI | GitHub Actions |
| Windows | AppVeyor¹ / Azure Pipelines / GitLab¹                  | Travis CI             | Cirrus CI | GitHub Actions |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.9.
