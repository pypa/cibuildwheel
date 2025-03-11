---
title: 'Pyodide'
---

# Pyodide (WebAssembly) builds (experimental)

## Prerequisites

You need to have a matching host version of Python (unlike all other cibuildwheel platforms). Linux host highly recommended; macOS hosts may work (e.g. invoking `pytest` directly in [`CIBW_TEST_COMMAND`](../options.md#test-command) is [currently failing](https://github.com/pyodide/pyodide/issues/4802)) and Windows hosts will not work.

## Specifying a pyodide build

You must target pyodide with `--platform pyodide` (or use `--only` on the identifier).
