This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.8                              | 3.9       | 3.10      | 3.11    | 3.12                                             |
|---------|----------------------------------|-----------|-----------|---------|--------------------------------------------------|
| Linux   | Azure Pipelines / GitHub Actions | Travis CI | Cirrus CI |         | AppVeyor¹ / CircleCI¹ / GitHub Actions / GitLab¹ |
| macOS   | Azure Pipelines                  |           | Cirrus CI | GitLab¹ | AppVeyor¹ /CircleCI¹ / GitHub Actions            |
| Windows | Azure Pipelines                  | Travis CI | Cirrus CI |         | AppVeyor¹ / GitHub Actions / GitLab¹             |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.9.
