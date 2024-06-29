This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.8                                                    | 3.9       | 3.10      | 3.12                                 |
|---------|--------------------------------------------------------|-----------|-----------|--------------------------------------|
| Linux   | AppVeyor¹ / Azure Pipelines / GitLab¹ / GitHub Actions | Travis CI | Cirrus CI | CircleCI¹ / GitHub Actions           |
| macOS   | AppVeyor¹ / Azure Pipelines                            |           | Cirrus CI | CircleCI¹ / GitHub Actions           |
| Windows | AppVeyor¹ / Azure Pipelines / GitLab¹                  | Travis CI | Cirrus CI | GitHub Actions  / GitLab¹            |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.9.
