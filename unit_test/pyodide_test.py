from cibuildwheel.platforms import pyodide


def test_all_python_configurations_accept_sha256() -> None:
    python_configurations = pyodide.all_python_configurations()

    assert python_configurations
    assert all(config.sha256 for config in python_configurations)
