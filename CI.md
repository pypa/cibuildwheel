This is a summary of the Python versions and platforms covered by the different CI platforms:

|         | 3.7                   | 3.8                      | 3.9      | 3.10      | 3.11           |
|---------|-----------------------|--------------------------|----------|-----------|----------------|
| Linux   | AppVeyor¹ / Travis CI | Azure Pipelines / GitLab | CircleCI | Cirrus CI | GitHub Actions |
| macOS   | AppVeyor¹ / Travis CI | Azure Pipelines          | CircleCI | Cirrus CI | GitHub Actions |
| Windows | AppVeyor¹ / Travis CI | Azure Pipelines          |          | Cirrus CI | GitHub Actions |

> ¹ AppVeyor only runs the "basic" test to reduce load.

Non-x86 architectures are covered on Travis CI using Python 3.7.
