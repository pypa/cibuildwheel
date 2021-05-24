This is a summary of the Python versions and platforms covered by the different CI platforms:

|          | 3.6                          | 3.7                                      | 3.8              |
|----------|------------------------------|------------------------------------------|------------------|
| Linux    | Travis CI / CircleCI         | AppVeyor² / GitHub Actions               | Azure Pipelines  |
| macOS    | CircleCI                     | AppVeyor² / Travis CI¹ / GitHub Actions  | Azure Pipelines  |
| Windows  | Travis CI / Azure Pipelines  | AppVeyor² / GitHub Actions               | Azure Pipelines  |

> ¹ Python version not really pinned, but dependent on the (default) version of image used.
> ² AppVeyor only runs the "basic" test to reduce load.

Non-x86 architectures are covered on Travis CI using Python 3.6.
