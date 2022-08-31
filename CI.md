This is a summary of the Python versions and platforms covered by the different CI platforms:

|          | 3.7                   | 3.8                       | 3.9      | 3.10                      |
|----------|-----------------------|---------------------------|----------|---------------------------|
| Linux    | AppVeyor¹ / Travis CI | Azure Pipelines / GitLab  | CircleCI | GitHub Actions, Cirrus CI |
| macOS    | AppVeyor¹ / Travis CI | Azure Pipelines           | CircleCI | GitHub Actions, Cirrus CI |
| Windows  | AppVeyor¹ / Travis CI | Azure Pipelines           |          | GitHub Actions, Cirrus CI |

> ¹ AppVeyor only runs the "basic" test to reduce load.

Non-x86 architectures are covered on Travis CI using Python 3.7.
