---
title: 'Windows'
---

# Windows builds

## Pre-requisites

You must have native build tools (i.e., Visual Studio) installed.

Because the builds are happening without full isolation, there might be some differences compared to CI builds (Visual Studio version, OS version, local files, ...) that might prevent you from finding an issue only seen in CI.

In order to speed-up builds, cibuildwheel will cache the tools it needs to be reused for future builds. The folder used for caching is system/user dependent and is reported in the printed preamble of each run (e.g. `Cache folder: C:\Users\Matt\AppData\Local\pypa\cibuildwheel\Cache`).

You can override the cache folder using the ``CIBW_CACHE_PATH`` environment variable.
