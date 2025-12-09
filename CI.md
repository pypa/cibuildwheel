This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.11                             | 3.12                            | 3.13           | 3.14           |
|---------|----------------------------------|---------------------------------|----------------|----------------|
| Linux   | Azure Pipelines / GitHub Actions | CircleCI¹ / Cirrus CI / GitLab¹ | GitHub Actions | GitHub Actions |
| macOS   | Azure Pipelines                  | CircleCI¹ / Cirrus CI / GitLab¹ | GitHub Actions |                |
| Windows | Azure Pipelines                  | Cirrus CI / GitLab¹             | GitHub Actions |                |

> ¹ Runs a reduced set of tests to reduce CI load
