This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.11                             | 3.12                                                    | 3.13           |
|---------|----------------------------------|---------------------------------------------------------|----------------|
| Linux   | Azure Pipelines / GitHub Actions | AppVeyor¹ / CircleCI¹ / Cirrus CI / GitLab¹ / Travis CI | GitHub Actions |
| macOS   | Azure Pipelines                  | AppVeyor¹ / CircleCI¹ / Cirrus CI / GitLab¹             | GitHub Actions |
| Windows | Azure Pipelines                  | AppVeyor¹ / Cirrus CI / GitLab¹ / Travis CI             | GitHub Actions |

> ¹ Runs a reduced set of tests to reduce CI load

Non-x86 architectures are covered on Travis CI using Python 3.12.
