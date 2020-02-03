This is a summary of the Python versions and platforms covered by the different CI platforms:

|          | 3.5              | 3.6              | 3.7                   | 3.8              |
|----------|------------------|------------------|-----------------------|------------------|
| Linux    | Travis CI        | CircleCI         | AppVeyor              | Azure Pipelines  |
| macOS    | Azure Pipelines  | CircleCI         | Travis CI¹ / CircleCI | Azure Pipelines  |
| Windows  | TravisCI         | Azure Pipelines  | AppVeyor              | Azure Pipelines  |

> ¹ Python version not really pinned, but dependent on the (default) version of image used.
