This is a summary of the Python versions and platforms covered by the different CI platforms:

|          | 3.5              | 3.6              | 3.7                                               | 3.8              |
|----------|------------------|------------------|---------------------------------------------------|------------------|
| Linux    | Travis CI        | CircleCI         | AppVeyor / GitHub Actions                         | Azure Pipelines  |
| macOS    | Azure Pipelines  | CircleCI         | AppVeyor / Travis CI¹ / CircleCI / GitHub Actions | Azure Pipelines  |
| Windows  | TravisCI         | Azure Pipelines  | AppVeyor / GitHub Actions                         | Azure Pipelines  |

> ¹ Python version not really pinned, but dependent on the (default) version of image used.

Non-x86 architectures are covered on Travis CI using Python 3.5.
