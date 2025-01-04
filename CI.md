This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.11                                         | 3.12                                        | 3.13           |
|---------|----------------------------------------------|---------------------------------------------|----------------|
| Linux   | Azure Pipelines / GitHub Actions / Travis CI | AppVeyor¹ / CircleCI¹ / Cirrus CI / GitLab¹ | GitHub Actions |
| macOS   | Azure Pipelines / GitLab¹                    | AppVeyor¹ / CircleCI¹ / Cirrus CI / GitLab¹ | GitHub Actions |
| Windows | Azure Pipelines / Travis CI                  | AppVeyor¹ / Cirrus CI / GitLab¹             | GitHub Actions |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.11.
