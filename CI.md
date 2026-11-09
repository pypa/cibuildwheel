This is a summary of the host Python versions and platforms covered by the different CI platforms:

|         | 3.11           | 3.12      | 3.13    | 3.14           | 3.15                             |
|---------|----------------|-----------|---------|----------------|----------------------------------|
| Linux   | GitHub Actions | CircleCI¹ | GitLab¹ | GitHub Actions | Azure Pipelines / GitHub Actions |
| macOS   |                | CircleCI¹ | GitLab¹ | GitHub Actions | Azure Pipelines                  |
| Windows |                |           | GitLab¹ | GitHub Actions | Azure Pipelines                  |

> ¹ Runs a reduced set of tests to reduce CI load
