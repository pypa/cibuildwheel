This is a summary of the Python versions and platforms covered by the different CI platforms:

|          | 3.6                          | 3.7                         | 3.8              |
|----------|------------------------------|-----------------------------|------------------|
| Linux    | Travis CI / CircleCI         | AppVeyor¹ / GitHub Actions  | Azure Pipelines  |
| macOS    | CircleCI                     | AppVeyor¹ / GitHub Actions  | Azure Pipelines  |
| Windows  | Travis CI / Azure Pipelines  | AppVeyor¹ / GitHub Actions  | Azure Pipelines  |

> ¹ AppVeyor only runs the "basic" test to reduce load.

Non-x86 architectures are covered on Travis CI using Python 3.6.
