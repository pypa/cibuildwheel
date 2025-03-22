---
title: 'Pyodide'
---

# Pyodide (WebAssembly) builds (experimental)

## Prerequisites

You need to have a matching host version of Python (unlike all other cibuildwheel platforms). Linux host highly recommended; macOS hosts may work (e.g. invoking `pytest` directly in [`CIBW_TEST_COMMAND`](../options.md#test-command) is [currently failing](https://github.com/pyodide/pyodide/issues/4802)) and Windows hosts will not work.

## Specifying a pyodide build

You must target pyodide with `--platform pyodide` (or use `--only` on the identifier).

!!!tip

    It is also possible to target a specific Pyodide version by setting the `CIBW_PYODIDE_VERSION` environment variable to the desired version. Users are responsible for setting an appropriate Pyodide version according to the `pyodide-build` version. A list is available in Pyodide's [cross-build environments metadata file](https://github.com/pyodide/pyodide/blob/main/pyodide-cross-build-environments.json) or can be
    referenced using the `pyodide xbuildenv search` command.

    This option is **not available** in the `pyproject.toml` config.
